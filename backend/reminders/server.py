"""
FastAPI server for Apple Reminders proxy.

Run this on the Mac host to allow Docker containers to create reminders.
Usage: python -m reminders.server
"""

import os
import logging
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from reminders.eventkit_store import _store

load_dotenv()

# --- File logging setup ---
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "reminders_proxy.log"

logger = logging.getLogger("reminders_proxy")
logger.setLevel(logging.DEBUG)

_file_handler = logging.FileHandler(LOG_FILE)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
logger.addHandler(_file_handler)

# Also keep a stream handler so uvicorn's stdout isn't totally silent
_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(logging.INFO)
_stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_stream_handler)

app = FastAPI(title="Apple Reminders Proxy")


class ReminderRequest(BaseModel):
    list_name: str
    reminder_text: str


class BatchDeleteRequest(BaseModel):
    list_name: str
    reminder_texts: list[str]


class ListRequest(BaseModel):
    list_name: str


def _ek_call(caller: str, fn, *args):
    """Call an EventKitStore method, log timing and result. Returns (success, result)."""
    logger.debug("[%s] EventKit call: %s%r", caller, fn.__name__, args)
    start = time.monotonic()
    try:
        success, result = fn(*args)
        elapsed = time.monotonic() - start
        if success:
            logger.info("[%s] EventKit OK (%.2fs) result=%r", caller, elapsed, result)
        else:
            logger.error("[%s] EventKit FAILED (%.2fs) error=%r", caller, elapsed, result)
        return success, result
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.exception("[%s] Unexpected EventKit error (%.2fs)", caller, elapsed)
        return False, str(e)


@app.post("/reminder")
def create_reminder(request: ReminderRequest):
    """Create a reminder in the specified list."""
    logger.info("POST /reminder  list=%r text=%r", request.list_name, request.reminder_text)
    success, output = _ek_call("POST /reminder", _store.create_reminder,
                               request.list_name, request.reminder_text)
    if not success:
        logger.error("POST /reminder FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {output}")
    return {"success": True}


@app.get("/lists")
def get_all_lists():
    """Get all Reminders lists."""
    logger.info("GET /lists")
    success, output = _ek_call("GET /lists", _store.get_all_lists)
    if not success:
        logger.warning("GET /lists returning empty — EventKit failed: %s", output)
        return {"lists": []}

    logger.info("GET /lists returning %d lists: %s", len(output), output)
    return {"lists": output}


@app.get("/lists/{list_name}/exists")
def list_exists(list_name: str):
    """Check if a Reminders list exists."""
    logger.info("GET /lists/%s/exists", list_name)
    success, output = _ek_call(f"GET /lists/{list_name}/exists", _store.list_exists, list_name)
    if not success:
        logger.warning("GET /lists/%s/exists returning False — EventKit failed: %s", list_name, output)
        return {"exists": False}

    logger.info("GET /lists/%s/exists → %s", list_name, output)
    return {"exists": output}


@app.post("/lists")
def create_list(request: ListRequest):
    """Create a new Reminders list."""
    logger.info("POST /lists  list_name=%r", request.list_name)
    success, output = _ek_call("POST /lists", _store.create_list, request.list_name)
    if not success:
        logger.error("POST /lists FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to create list: {output}")
    return {"success": True}


@app.get("/lists/{list_name}/items")
def get_list_items(list_name: str):
    """Get all incomplete reminders from a list."""
    logger.info("GET /lists/%s/items", list_name)
    success, output = _ek_call(f"GET /lists/{list_name}/items", _store.get_list_items, list_name)
    if not success:
        logger.warning("GET /lists/%s/items returning empty — EventKit failed: %s", list_name, output)
        return {"items": []}

    logger.info("GET /lists/%s/items returning %d items", list_name, len(output))
    return {"items": output}


@app.delete("/reminder")
def delete_reminder(request: ReminderRequest):
    """Delete a reminder by exact text match."""
    logger.info("DELETE /reminder  list=%r text=%r", request.list_name, request.reminder_text)
    success, output = _ek_call("DELETE /reminder", _store.delete_reminder,
                               request.list_name, request.reminder_text)
    if not success:
        logger.error("DELETE /reminder FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder: {output}")
    return {"success": True}


@app.delete("/reminders/batch")
def delete_reminders_batch(request: BatchDeleteRequest):
    """Delete multiple reminders in a single batched EventKit commit."""
    logger.info("DELETE /reminders/batch  list=%r  count=%d texts=%r",
                request.list_name, len(request.reminder_texts), request.reminder_texts)
    if not request.reminder_texts:
        logger.info("DELETE /reminders/batch — empty list, nothing to do")
        return {"success": True}

    success, output = _ek_call("DELETE /reminders/batch", _store.delete_reminders_batch,
                               request.list_name, request.reminder_texts)
    if not success:
        logger.error("DELETE /reminders/batch FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to batch delete reminders: {output}")
    return {"success": True}


@app.get("/health")
def health_check():
    """Health check — verifies that EventKit can talk to Reminders."""
    logger.debug("GET /health")
    success, output = _ek_call("GET /health", _store.get_default_list_name)
    if success:
        logger.info("GET /health OK — Reminders accessible, default list=%r", output)
        return {"status": "ok", "reminders_accessible": True, "default_list": output}
    else:
        logger.warning("GET /health — server up but Reminders NOT accessible: %s", output)
        return {"status": "degraded", "reminders_accessible": False, "error": output}


@app.on_event("startup")
def on_startup():
    logger.info("=" * 60)
    logger.info("Reminders proxy starting up")
    logger.info("Log file: %s", LOG_FILE)
    logger.info("PID: %d", os.getpid())
    logger.info("=" * 60)

    # Pre-flight: request EventKit access (blocks until TCC dialog resolved)
    success, output = _store.request_access()
    if success:
        logger.info("Startup preflight PASSED — EventKit Reminders access granted")
    else:
        logger.error(
            "Startup preflight FAILED — Reminders is NOT accessible: %s. "
            "The proxy will start but all EventKit calls will fail until "
            "the TCC permission is granted. Open System Settings > Privacy & Security > "
            "Reminders and ensure this Python/Terminal process is allowed.",
            output,
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("REMINDERS_PROXY_PORT", "8765"))
    logger.info("Starting uvicorn on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
