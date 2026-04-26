import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from server.sse import serialize_model, session_start_event
from server.sessions import Session, sessions
from server.graph_runner import stream_graph_execution
from .models import PlanRequest, ResumeRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/plan")
async def start_plan(body: PlanRequest, request: Request):
    """
    Start a new meal planning session.

    Supports two entry modes:
    - Search mode: Provide cuisine_type to search for recipes
    - URL mode: Provide direct_url to skip directly to processing a specific recipe

    Returns an SSE stream. First event is 'session_start' with the session_id.
    """
    logger.info(
        f"POST /plan - cuisine_type={body.cuisine_type!r}, "
        f"direct_url={body.direct_url!r}, preferred_sources={body.preferred_sources}"
    )

    session_id = str(uuid.uuid4())[:8]
    session = Session(
        session_id,
        cuisine_type=body.cuisine_type,
        direct_url=body.direct_url,
        preferred_sources=body.preferred_sources,
        checkpointer=request.app.state.checkpointer,
    )
    sessions[session_id] = session
    logger.info(f"POST /plan - created session {session_id}")

    initial_state = {
        "direct_url": body.direct_url if body.direct_url else None,
        "cuisine_type": body.cuisine_type,
        "preferred_sources": body.preferred_sources,
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


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, body: ResumeRequest):
    """Resume a session from an interrupt. Returns an SSE stream."""
    logger.info(f"POST /sessions/{session_id}/resume - input={body.input!r}")

    session = sessions.get(session_id)
    if not session:
        logger.warning(f"POST /sessions/{session_id}/resume - session not found")
        raise HTTPException(status_code=404, detail="Session not found")
    if session.completed:
        logger.warning(f"POST /sessions/{session_id}/resume - session already completed")
        raise HTTPException(status_code=400, detail="Session already completed")

    async def event_generator():
        async for event in stream_graph_execution(session, resume_input=body.input):
            yield event

    return EventSourceResponse(event_generator())


@router.get("/sessions/{session_id}")
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


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    logger.info(f"DELETE /sessions/{session_id}")
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f"DELETE /sessions/{session_id} - deleted")
        return {"deleted": True}
    logger.warning(f"DELETE /sessions/{session_id} - session not found")
    raise HTTPException(status_code=404, detail="Session not found")
