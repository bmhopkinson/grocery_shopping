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

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langgraph.types import Command

from meal_planner import build_meal_planner_graph, get_checkpointer_async
from server.sse import (
    sse_event,
    serialize_model,
    session_start_event,
    status_event,
    error_event,
    complete_event,
    grocery_list_event,
)
from server.interrupts import detect_interrupt


logger = logging.getLogger(__name__)


# Shared checkpointer (initialized on startup)
_checkpointer = None


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

class Session:
    """Holds state for an active meal planning session."""

    def __init__(
        self,
        session_id: str,
        cuisine_type: str = "",
        direct_url: str = "",
        preferred_sources: list[str] = None
    ):
        self.session_id = session_id
        self.cuisine_type = cuisine_type
        self.direct_url = direct_url
        self.preferred_sources = preferred_sources or []
        self.thread_id = f"session-{session_id}"
        self.graph = build_meal_planner_graph(checkpointer=_checkpointer)
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
# Node Status Messages
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Stream Graph Execution
# ---------------------------------------------------------------------------

def _build_invoke_input(
    initial_input: Optional[dict],
    resume_input: Optional[str]
):
    """Build the input for graph invocation."""
    if resume_input is not None:
        return Command(resume=resume_input)
    if initial_input is not None:
        return initial_input
    raise ValueError("Must provide either initial_input or resume_input")


def _extract_status_event(event: dict) -> Optional[dict]:
    """Extract status event from graph stream event if applicable."""
    if event.get("event") == "on_chain_start":
        node_name = event.get("name")
        if node_name in NODE_MESSAGES:
            return status_event(node_name, NODE_MESSAGES[node_name])
    return None


def _handle_interrupt(state) -> dict:
    """Handle an interrupt state and return the appropriate SSE event."""
    # Extract interrupt value
    interrupt_value = None
    if state.tasks and state.tasks[0].interrupts:
        interrupt_value = state.tasks[0].interrupts[0].value

    next_node = state.next[0] if state.next else None

    # Use the interrupt registry to detect and build event
    match = detect_interrupt(next_node, interrupt_value)
    return sse_event(match.event_name, match.event_data)


async def _handle_completion(session: Session, state) -> AsyncGenerator[dict, None]:
    """Handle graph completion and yield final events."""
    session.completed = True
    values = state.values

    # Check for errors in state
    error = values.get("error")
    if error:
        yield error_event(error)
        return

    # Extract completion data
    selected_meal = values.get("selected_meal")
    grocery_list = values.get("grocery_list", [])
    reminders_added = values.get("reminders_added", False)

    # Emit grocery list if present
    if grocery_list:
        yield grocery_list_event(grocery_list)

    # Emit completion
    yield complete_event(selected_meal, grocery_list, reminders_added)


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

    logger.debug(f"stream_graph_execution started for session {session.session_id}")

    try:
        # Determine invocation input
        invoke_input = _build_invoke_input(initial_input, resume_input)

        # Stream node execution events
        async for event in graph.astream_events(invoke_input, config=config, version="v2"):
            status = _extract_status_event(event)
            if status:
                yield status

        # Check final state
        state = await graph.aget_state(config)
        session.last_state = state

        # Handle interrupt or completion
        if state.next:
            yield _handle_interrupt(state)
        else:
            async for event in _handle_completion(session, state):
                yield event

    except Exception as e:
        logger.exception(f"Error in stream_graph_execution: {e}")
        yield error_event(str(e))


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize checkpointer on startup, cleanup on shutdown."""
    global _checkpointer
    logger.info("FastAPI lifespan startup - initializing checkpointer...")
    try:
        _checkpointer = await get_checkpointer_async()
        logger.info(f"Checkpointer initialized: {type(_checkpointer).__name__}")
    except Exception as e:
        logger.exception(f"Failed to initialize checkpointer: {e}")
        raise
    yield
    logger.info("FastAPI lifespan shutdown - clearing sessions...")
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
    logger.debug(f"/plan endpoint called: cuisine_type={request.cuisine_type}, direct_url={request.direct_url}")

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
        yield session_start_event(session_id)

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
            k: serialize_model(v)
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
