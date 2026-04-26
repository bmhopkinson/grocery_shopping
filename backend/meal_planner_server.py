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
- reminders_prompt: {items: [...], working_lists: [{id, name}], prompt: str, instruction: str} - Interrupt for list selection
- grocery_list: {items: [...]} - Final grocery list
- complete: {selected_meal: {...}, grocery_list: [...], reminders_added: bool}
- error: {message: str}

Usage: uvicorn meal_planner_server:app --host 0.0.0.0 --port 8000
"""

import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.meal_planner import get_checkpointer_async
from database import init_engine, close_engine
from server.sessions import sessions
from api import all_routers


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


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize checkpointer and database engine on startup, cleanup on shutdown."""
    logger.info("FastAPI lifespan startup - initializing checkpointer...")
    try:
        app.state.checkpointer = await get_checkpointer_async()
        logger.info(f"Checkpointer initialized: {type(app.state.checkpointer).__name__}")
    except Exception as e:
        logger.exception(f"Failed to initialize checkpointer: {e}")
        raise
    await init_engine()
    logger.info("SQLAlchemy engine and tables ready")
    yield
    await close_engine()
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

for router in all_routers:
    app.include_router(router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    logger.debug(f"GET /health - active_sessions={len(sessions)}")
    return {"status": "ok", "active_sessions": len(sessions)}
