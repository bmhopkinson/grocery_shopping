"""
FastAPI server for Meal Planner with SSE streaming.

Endpoints:
- POST /plan - Start a new meal planning session, returns SSE stream
- POST /sessions/{session_id}/resume - Resume from an interrupt, returns SSE stream

Event types sent via SSE:
- session_start: {session_id: str} - First event with session ID
- status: {node: str, message: str} - Progress updates
- meal_options: {options: [...], prompt: str, instruction: str} - Interrupt for meal selection
- ingredient_review: {ingredients: [...], prompt: str, instruction: str} - Interrupt for ingredient review
- reminders_prompt: {items: [...], existing_lists: [...], prompt: str, instruction: str} - Interrupt for reminders list
- grocery_list: {items: [...]} - Final grocery list
- complete: {selected_meal: {...}, grocery_list: [...], reminders_added: bool}
- error: {message: str}

Usage: uvicorn meal_planner_server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from meal_planner import build_meal_planner_graph
from langgraph.types import Command


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

class Session:
    """Holds state for an active meal planning session."""

    def __init__(self, session_id: str, cuisine_type: str = "", direct_url: str = "", preferred_sources: list[str] = None):
        self.session_id = session_id
        self.cuisine_type = cuisine_type
        self.direct_url = direct_url
        self.preferred_sources = preferred_sources or []
        self.thread_id = f"session-{session_id}"
        self.graph = build_meal_planner_graph()
        self.started = False
        self.completed = False
        self.last_state = None


# In-memory session store (use Redis for production)
sessions: dict[str, Session] = {}


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    cuisine_type: str = ""
    direct_url: str = ""  # Direct recipe URL (skips search if provided)
    preferred_sources: list[str] = []


class ResumeRequest(BaseModel):
    input: str


# ---------------------------------------------------------------------------
# Event Helpers
# ---------------------------------------------------------------------------

def sse_event(event_type: str, data: dict) -> dict:
    """Format an SSE event."""
    import json
    return {
        "event": event_type,
        "data": json.dumps(data)
    }


# Node name to user-friendly status message
NODE_MESSAGES = {
    "create_meal_from_url": "Fetching recipe from URL...",
    "search_meals": "Searching for recipes...",
    "parse_meals": "Analyzing search results...",
    "validate_recipes": "Validating recipe URLs...",
    "refine_search": "Refining search with specific dishes...",
    "present_options": "Preparing meal options...",
    "process_meal": "Processing selected meal...",
    "extract_ingredients": "Extracting ingredients from recipe...",
    "review_ingredients": "Preparing ingredient list for review...",
    "add_to_reminders": "Adding items to reminders...",
}


async def stream_graph_execution(
    session: Session,
    initial_input: Optional[dict] = None,
    resume_input: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """
    Stream graph execution as SSE events.

    Yields events until completion or an interrupt is hit.
    """
    config = {"configurable": {"thread_id": session.thread_id}}
    graph = session.graph

    try:
        # Determine what to invoke with
        if resume_input is not None:
            invoke_input = Command(resume=resume_input)
        elif initial_input is not None:
            invoke_input = initial_input
        else:
            raise ValueError("Must provide either initial_input or resume_input")

        # Stream the graph execution
        async for event in graph.astream_events(invoke_input, config=config, version="v2"):
            event_type = event.get("event")

            # Node start events -> status updates
            if event_type == "on_chain_start":
                node_name = event.get("name")
                if node_name in NODE_MESSAGES:
                    yield sse_event("status", {
                        "node": node_name,
                        "message": NODE_MESSAGES[node_name]
                    })

            # Check for completion after stream ends

        # After streaming, check the final state
        state = graph.get_state(config)
        session.last_state = state

        # Check if we hit an interrupt
        if state.next:
            # There's an interrupt - determine which type
            interrupt_value = None
            if state.tasks and state.tasks[0].interrupts:
                interrupt_value = state.tasks[0].interrupts[0].value

            next_node = state.next[0] if state.next else None

            # Detect interrupt type based on the interrupt value's instruction field
            # This is more reliable than node names when using subgraphs
            instruction = interrupt_value.get("instruction", "") if interrupt_value else ""

            if next_node == "present_options" or "select a recipe" in instruction.lower():
                # Meal selection interrupt
                # Get options from the interrupt value (passed by the node)
                options_data = interrupt_value.get("options", []) if interrupt_value else []
                yield sse_event("meal_options", {
                    "options": options_data,
                    "prompt": interrupt_value.get("prompt", "Select a meal:") if interrupt_value else "Select a meal:",
                    "instruction": instruction
                })
            elif "remove" in instruction.lower() or "approve" in instruction.lower():
                # Ingredient review interrupt (from instruction pattern)
                # Get ingredients from the interrupt value (passed by the node), not state
                ingredients_data = interrupt_value.get("ingredients", []) if interrupt_value else []
                yield sse_event("ingredient_review", {
                    "ingredients": ingredients_data,
                    "prompt": interrupt_value.get("prompt", "Review ingredients:") if interrupt_value else "Review ingredients:",
                    "instruction": instruction
                })
            elif "list number" in instruction.lower() or "skip" in instruction.lower():
                # Reminders list selection interrupt (from instruction pattern)
                # Get items from the interrupt value (passed by the node), not state
                items_data = interrupt_value.get("items", []) if interrupt_value else []
                yield sse_event("reminders_prompt", {
                    "items": items_data,
                    "existing_lists": interrupt_value.get("existing_lists", []) if interrupt_value else [],
                    "prompt": interrupt_value.get("prompt", "Select a reminders list:") if interrupt_value else "Select a reminders list:",
                    "instruction": instruction
                })
            else:
                # Generic interrupt
                yield sse_event("interrupt", {
                    "next_node": next_node,
                    "prompt": interrupt_value.get("prompt", "Input required:") if interrupt_value else "Input required:",
                    "data": interrupt_value if interrupt_value else {}
                })
        else:
            # Graph completed
            session.completed = True
            values = state.values

            selected_meal = values.get("selected_meal")
            grocery_list = values.get("grocery_list", [])
            reminders_added = values.get("reminders_added", False)

            # Send grocery list event
            if grocery_list:
                yield sse_event("grocery_list", {
                    "items": [item.model_dump() for item in grocery_list]
                })

            # Send completion event
            yield sse_event("complete", {
                "selected_meal": selected_meal.model_dump() if selected_meal else None,
                "grocery_list": [item.model_dump() for item in grocery_list] if grocery_list else [],
                "reminders_added": reminders_added
            })

    except Exception as e:
        yield sse_event("error", {"message": str(e)})


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cleanup sessions on shutdown."""
    yield
    sessions.clear()


app = FastAPI(
    title="Meal Planner API",
    description="SSE-based API for the meal planning agent",
    lifespan=lifespan
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/plan")
async def start_plan(request: PlanRequest):
    """
    Start a new meal planning session.

    Supports two entry modes:
    - Search mode: Provide cuisine_type to search for recipes
    - URL mode: Provide direct_url to skip directly to processing a specific recipe

    Returns an SSE stream with events for the planning process.
    First event will be 'session_start' with the session_id needed for /resume.
    """
    session_id = str(uuid.uuid4())[:8]
    session = Session(
        session_id,
        cuisine_type=request.cuisine_type,
        direct_url=request.direct_url,
        preferred_sources=request.preferred_sources
    )
    sessions[session_id] = session

    initial_state = {
        "direct_url": request.direct_url if request.direct_url else None,
        "cuisine_type": request.cuisine_type,
        "preferred_sources": request.preferred_sources,
        "search_results": None,
        "meal_options": None,
        "selected_meal": None,
        "messages": [],
        "refinement_count": 0,
        "refine_dishes": None,
        "grocery_list": None,
        "reminders_added": None
    }

    async def event_generator():
        # First event: session ID
        yield sse_event("session_start", {"session_id": session_id})

        # Stream graph execution
        async for event in stream_graph_execution(session, initial_input=initial_state):
            yield event

    return EventSourceResponse(event_generator())


@app.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, request: ResumeRequest):
    """
    Resume a session from an interrupt.

    Returns an SSE stream continuing from where the interrupt occurred.
    """
    session = sessions.get(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.completed:
        raise HTTPException(status_code=400, detail="Session already completed")

    async def event_generator():
        async for event in stream_graph_execution(session, resume_input=request.input):
            yield event

    return EventSourceResponse(event_generator())


@app.get("/sessions/{session_id}")
async def get_session_state(session_id: str):
    """Get the current state of a session (for debugging/recovery)."""
    session = sessions.get(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session.last_state
    if not state:
        return {
            "session_id": session_id,
            "cuisine_type": session.cuisine_type,
            "completed": session.completed,
            "state": None
        }

    return {
        "session_id": session_id,
        "cuisine_type": session.cuisine_type,
        "completed": session.completed,
        "next": list(state.next) if state.next else [],
        "values": {
            k: (v.model_dump() if hasattr(v, 'model_dump') else
                [i.model_dump() for i in v] if isinstance(v, list) and v and hasattr(v[0], 'model_dump') else v)
            for k, v in state.values.items()
        }
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "active_sessions": len(sessions)}
