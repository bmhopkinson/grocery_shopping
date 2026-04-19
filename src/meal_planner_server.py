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
import logging
import logging.handlers
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import reminders as reminders_client
from meal_planner import get_checkpointer_async, get_connection_pool
from usuals import init_usuals_table, get_usuals, create_usual, update_usual, delete_usual
from server.sse import serialize_model, session_start_event
from server.sessions import Session, sessions
from server.graph_runner import stream_graph_execution
from server.reorder import reorder_reminders_list


# ---------------------------------------------------------------------------
# File Logging Setup
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "meal_planner_server.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
)
logger.addHandler(_file_handler)


# Shared checkpointer (initialized on startup)
_checkpointer = None


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    cuisine_type: str = ""
    direct_url: str = ""
    preferred_sources: list[str] = []


class ResumeRequest(BaseModel):
    input: Union[str, dict]


class UsualCreateRequest(BaseModel):
    name: str
    category: Optional[str] = None


class UsualUpdateRequest(BaseModel):
    name: str
    category: Optional[str] = None


class AddUsualsToRemindersRequest(BaseModel):
    usual_ids: list[str]
    list_name: str


class ReorderRemindersRequest(BaseModel):
    list_name: str


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize checkpointer and usuals table on startup, cleanup on shutdown."""
    global _checkpointer
    logger.info("FastAPI lifespan startup - initializing checkpointer...")
    try:
        _checkpointer = await get_checkpointer_async()
        logger.info(f"Checkpointer initialized: {type(_checkpointer).__name__}")
    except Exception as e:
        logger.exception(f"Failed to initialize checkpointer: {e}")
        raise
    pool = get_connection_pool()
    await init_usuals_table(pool)
    logger.info("Usuals table ready")
    yield
    logger.info("FastAPI lifespan shutdown - clearing sessions...")
    sessions.clear()


app = FastAPI(
    title="Meal Planner API",
    description="SSE-based API for the meal planning agent",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Planning routes
# ---------------------------------------------------------------------------

@app.post("/plan")
async def start_plan(request: PlanRequest):
    """
    Start a new meal planning session.

    Supports two entry modes:
    - Search mode: Provide cuisine_type to search for recipes
    - URL mode: Provide direct_url to skip directly to processing a specific recipe

    Returns an SSE stream. First event is 'session_start' with the session_id.
    """
    logger.info(
        f"POST /plan - cuisine_type={request.cuisine_type!r}, "
        f"direct_url={request.direct_url!r}, preferred_sources={request.preferred_sources}"
    )

    session_id = str(uuid.uuid4())[:8]
    session = Session(
        session_id,
        cuisine_type=request.cuisine_type,
        direct_url=request.direct_url,
        preferred_sources=request.preferred_sources,
        checkpointer=_checkpointer,
    )
    sessions[session_id] = session
    logger.info(f"POST /plan - created session {session_id}")

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
        "reminders_added": None,
    }

    async def event_generator():
        yield session_start_event(session_id)
        async for event in stream_graph_execution(session, initial_input=initial_state):
            yield event

    return EventSourceResponse(event_generator())


@app.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, request: ResumeRequest):
    """Resume a session from an interrupt. Returns an SSE stream."""
    logger.info(f"POST /sessions/{session_id}/resume - input={request.input!r}")

    session = sessions.get(session_id)
    if not session:
        logger.warning(f"POST /sessions/{session_id}/resume - session not found")
        raise HTTPException(status_code=404, detail="Session not found")
    if session.completed:
        logger.warning(f"POST /sessions/{session_id}/resume - session already completed")
        raise HTTPException(status_code=400, detail="Session already completed")

    async def event_generator():
        async for event in stream_graph_execution(session, resume_input=request.input):
            yield event

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Session management routes
# ---------------------------------------------------------------------------

@app.get("/sessions/{session_id}")
async def get_session_state(session_id: str):
    """Get the current state of a session (for debugging/recovery)."""
    logger.info(f"GET /sessions/{session_id}")

    session = sessions.get(session_id)
    if not session:
        logger.warning(f"GET /sessions/{session_id} - session not found")
        raise HTTPException(status_code=404, detail="Session not found")

    state = session.last_state
    if not state:
        return {"session_id": session_id, "cuisine_type": session.cuisine_type, "completed": session.completed, "state": None}

    return {
        "session_id": session_id,
        "cuisine_type": session.cuisine_type,
        "completed": session.completed,
        "next": list(state.next) if state.next else [],
        "values": {k: serialize_model(v) for k, v in state.values.items()},
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    logger.info(f"DELETE /sessions/{session_id}")
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f"DELETE /sessions/{session_id} - deleted")
        return {"deleted": True}
    logger.warning(f"DELETE /sessions/{session_id} - session not found")
    raise HTTPException(status_code=404, detail="Session not found")


# ---------------------------------------------------------------------------
# Reminders routes
# ---------------------------------------------------------------------------

@app.get("/reminder-lists")
async def get_reminder_lists():
    """Return all Apple Reminders list names."""
    lists = await asyncio.to_thread(reminders_client.get_all_lists)
    return {"lists": lists}


@app.post("/reorder-reminders")
async def reorder_reminders(request: ReorderRemindersRequest):
    """Reorder all items in a Reminders list by grocery store section order."""
    logger.info(f"POST /reorder-reminders - list_name={request.list_name!r}")
    return await reorder_reminders_list(request.list_name)


# ---------------------------------------------------------------------------
# Usuals routes
# ---------------------------------------------------------------------------

@app.get("/usuals")
async def list_usuals():
    pool = get_connection_pool()
    return await get_usuals(pool)


@app.post("/usuals/add-to-reminders")
async def add_usuals_to_reminders(request: AddUsualsToRemindersRequest):
    pool = get_connection_pool()
    all_usuals = await get_usuals(pool)
    id_set = set(request.usual_ids)
    selected = [u for u in all_usuals if u["id"] in id_set]

    if not selected:
        raise HTTPException(status_code=400, detail="No matching usuals found")

    list_exists = await asyncio.to_thread(reminders_client.list_exists, request.list_name)
    if not list_exists:
        await asyncio.to_thread(reminders_client.create_list, request.list_name)

    added, failed = [], []
    for item in selected:
        ok = await asyncio.to_thread(reminders_client.create_reminder, request.list_name, item["name"])
        (added if ok else failed).append(item["name"])

    logger.info(f"add_usuals_to_reminders: added={added}, failed={failed}, list={request.list_name!r}")
    return {"added": added, "failed": failed, "list_name": request.list_name}


@app.post("/usuals")
async def create_usual_endpoint(request: UsualCreateRequest):
    pool = get_connection_pool()
    return await create_usual(pool, request.name, request.category)


@app.put("/usuals/{id}")
async def update_usual_endpoint(id: str, request: UsualUpdateRequest):
    pool = get_connection_pool()
    item = await update_usual(pool, id, request.name, request.category)
    if item is None:
        raise HTTPException(status_code=404, detail="Usual not found")
    return item


@app.delete("/usuals/{id}")
async def delete_usual_endpoint(id: str):
    pool = get_connection_pool()
    deleted = await delete_usual(pool, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usual not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    logger.debug(f"GET /health - active_sessions={len(sessions)}")
    return {"status": "ok", "active_sessions": len(sessions)}
