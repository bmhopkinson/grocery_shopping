"""
FastAPI server for Apple Reminders proxy.

Run this on the Mac host to allow Docker containers to create reminders.
Usage: python reminders_server.py
"""

import os
import logging
import subprocess
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# --- File logging setup ---
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
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


def run_applescript(script: str, caller: str = "unknown", timeout: float = 30.0) -> tuple[bool, str]:
    """Run an AppleScript and return (success, output).

    Args:
        script: The AppleScript source to execute.
        caller: Name of the calling endpoint (for log context).
        timeout: Seconds before we kill the osascript process.
    """
    logger.debug("[%s] Executing AppleScript:\n%s", caller, script.strip())
    start = time.monotonic()
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        logger.info("[%s] AppleScript OK (%.2fs) stdout=%r", caller, elapsed, result.stdout.strip())
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        logger.error(
            "[%s] AppleScript TIMED OUT after %.2fs (limit=%.0fs). "
            "This usually means macOS is waiting for a TCC permission prompt that "
            "the user hasn't responded to, or Reminders.app is hung.",
            caller, elapsed, timeout,
        )
        return False, f"osascript timed out after {timeout}s"
    except subprocess.CalledProcessError as e:
        elapsed = time.monotonic() - start
        logger.error(
            "[%s] AppleScript FAILED (%.2fs) returncode=%d stderr=%r",
            caller, elapsed, e.returncode, e.stderr,
        )
        return False, e.stderr
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.exception("[%s] Unexpected error running AppleScript (%.2fs)", caller, elapsed)
        return False, str(e)


@app.post("/reminder")
def create_reminder(request: ReminderRequest):
    """Create a reminder in the specified list."""
    logger.info("POST /reminder  list=%r text=%r", request.list_name, request.reminder_text)
    escaped_text = request.reminder_text.replace('"', '\\"').replace('\\', '\\\\')
    escaped_list = request.list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            make new reminder with properties {{name:"{escaped_text}"}}
        end tell
    end tell
    '''

    success, output = run_applescript(script, caller="POST /reminder")
    if not success:
        logger.error("POST /reminder FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {output}")
    return {"success": True}


@app.get("/lists")
def get_all_lists():
    """Get all Reminders lists."""
    logger.info("GET /lists")
    script = '''
    tell application "Reminders"
        set listNames to name of every list
        return listNames
    end tell
    '''

    success, output = run_applescript(script, caller="GET /lists")
    if not success:
        logger.warning("GET /lists returning empty — AppleScript failed: %s", output)
        return {"lists": []}

    if not output:
        logger.info("GET /lists returning empty — no lists found")
        return {"lists": []}

    lists = [name.strip() for name in output.split(',')]
    logger.info("GET /lists returning %d lists: %s", len(lists), lists)
    return {"lists": lists}


@app.get("/lists/{list_name}/exists")
def list_exists(list_name: str):
    """Check if a Reminders list exists."""
    logger.info("GET /lists/%s/exists", list_name)
    script = f'''
    tell application "Reminders"
        set listNames to name of every list
        return listNames contains "{list_name}"
    end tell
    '''

    success, output = run_applescript(script, caller=f"GET /lists/{list_name}/exists")
    if not success:
        logger.warning("GET /lists/%s/exists returning False — AppleScript failed: %s", list_name, output)
        return {"exists": False}

    exists = output == "true"
    logger.info("GET /lists/%s/exists → %s", list_name, exists)
    return {"exists": exists}


@app.post("/lists")
def create_list(request: ListRequest):
    """Create a new Reminders list."""
    logger.info("POST /lists  list_name=%r", request.list_name)
    escaped_name = request.list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        make new list with properties {{name:"{escaped_name}"}}
    end tell
    '''

    success, output = run_applescript(script, caller="POST /lists")
    if not success:
        logger.error("POST /lists FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to create list: {output}")
    return {"success": True}


@app.get("/lists/{list_name}/items")
def get_list_items(list_name: str):
    """Get all incomplete reminders from a list."""
    logger.info("GET /lists/%s/items", list_name)
    escaped_list = list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set reminderNames to name of every reminder whose completed is false
            return reminderNames
        end tell
    end tell
    '''

    success, output = run_applescript(script, caller=f"GET /lists/{list_name}/items")
    if not success:
        logger.warning("GET /lists/%s/items returning empty — AppleScript failed: %s", list_name, output)
        return {"items": []}

    if not output:
        logger.info("GET /lists/%s/items returning empty — list has no incomplete items", list_name)
        return {"items": []}

    items = [name.strip() for name in output.split(',')]
    logger.info("GET /lists/%s/items returning %d items", list_name, len(items))
    return {"items": items}


@app.delete("/reminder")
def delete_reminder(request: ReminderRequest):
    """Delete a reminder by exact text match."""
    logger.info("DELETE /reminder  list=%r text=%r", request.list_name, request.reminder_text)
    escaped_text = request.reminder_text.replace('"', '\\"').replace('\\', '\\\\')
    escaped_list = request.list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set targetReminders to every reminder whose name is "{escaped_text}"
            repeat with r in targetReminders
                delete r
            end repeat
        end tell
    end tell
    '''

    success, output = run_applescript(script, caller="DELETE /reminder")
    if not success:
        logger.error("DELETE /reminder FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder: {output}")
    return {"success": True}


@app.delete("/reminders/batch")
def delete_reminders_batch(request: BatchDeleteRequest):
    """Delete multiple reminders in a single AppleScript call.

    This batches deletions to avoid overwhelming the TCC daemon with
    repeated permission checks, which can cause Reminders to hang.
    """
    logger.info("DELETE /reminders/batch  list=%r  count=%d texts=%r",
                request.list_name, len(request.reminder_texts), request.reminder_texts)
    if not request.reminder_texts:
        logger.info("DELETE /reminders/batch — empty list, nothing to do")
        return {"success": True}

    escaped_list = request.list_name.replace('"', '\\"')

    # Build AppleScript list of names to delete
    escaped_names = [text.replace('\\', '\\\\').replace('"', '\\"') for text in request.reminder_texts]
    names_list = ', '.join(f'"{name}"' for name in escaped_names)

    # Get all reminders once, then delete matching ones
    # This minimizes TCC permission checks vs doing N 'whose' queries
    script = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set namesToDelete to {{{names_list}}}
            set allReminders to every reminder whose completed is false
            repeat with r in allReminders
                if namesToDelete contains (name of r) then
                    delete r
                end if
            end repeat
        end tell
    end tell
    '''

    success, output = run_applescript(script, caller="DELETE /reminders/batch", timeout=60.0)
    if not success:
        logger.error("DELETE /reminders/batch FAILED: %s", output)
        raise HTTPException(status_code=500, detail=f"Failed to batch delete reminders: {output}")
    return {"success": True}


@app.get("/health")
def health_check():
    """Health check — also verifies that osascript can talk to Reminders."""
    logger.debug("GET /health")
    success, output = run_applescript(
        'tell application "Reminders" to return name of default list',
        caller="GET /health",
        timeout=10.0,
    )
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

    # Pre-flight: can we talk to Reminders at all?
    success, output = run_applescript(
        'tell application "Reminders" to return name of default list',
        caller="startup_preflight",
        timeout=15.0,
    )
    if success:
        logger.info("Startup preflight PASSED — Reminders accessible, default list=%r", output)
    else:
        logger.error(
            "Startup preflight FAILED — Reminders is NOT accessible: %s. "
            "The proxy will start but all AppleScript calls will fail until "
            "the TCC permission is granted. Open System Settings > Privacy & Security > "
            "Reminders and ensure this Python/Terminal process is allowed.",
            output,
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("REMINDERS_PROXY_PORT", "8765"))
    logger.info("Starting uvicorn on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
