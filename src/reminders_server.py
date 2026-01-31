"""
FastAPI server for Apple Reminders proxy.

Run this on the Mac host to allow Docker containers to create reminders.
Usage: python reminders_server.py
"""

import os
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Apple Reminders Proxy")


class ReminderRequest(BaseModel):
    list_name: str
    reminder_text: str


class BatchDeleteRequest(BaseModel):
    list_name: str
    reminder_texts: list[str]


class ListRequest(BaseModel):
    list_name: str


def run_applescript(script: str) -> tuple[bool, str]:
    """Run an AppleScript and return (success, output)."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            check=True,
            capture_output=True,
            text=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr


@app.post("/reminder")
def create_reminder(request: ReminderRequest):
    """Create a reminder in the specified list."""
    escaped_text = request.reminder_text.replace('"', '\\"').replace('\\', '\\\\')
    escaped_list = request.list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            make new reminder with properties {{name:"{escaped_text}"}}
        end tell
    end tell
    '''

    success, output = run_applescript(script)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {output}")
    return {"success": True}


@app.get("/lists")
def get_all_lists():
    """Get all Reminders lists."""
    script = '''
    tell application "Reminders"
        set listNames to name of every list
        return listNames
    end tell
    '''

    success, output = run_applescript(script)
    if not success:
        return {"lists": []}

    if not output:
        return {"lists": []}

    lists = [name.strip() for name in output.split(',')]
    return {"lists": lists}


@app.get("/lists/{list_name}/exists")
def list_exists(list_name: str):
    """Check if a Reminders list exists."""
    script = f'''
    tell application "Reminders"
        set listNames to name of every list
        return listNames contains "{list_name}"
    end tell
    '''

    success, output = run_applescript(script)
    if not success:
        return {"exists": False}

    return {"exists": output == "true"}


@app.post("/lists")
def create_list(request: ListRequest):
    """Create a new Reminders list."""
    escaped_name = request.list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        make new list with properties {{name:"{escaped_name}"}}
    end tell
    '''

    success, output = run_applescript(script)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to create list: {output}")
    return {"success": True}


@app.get("/lists/{list_name}/items")
def get_list_items(list_name: str):
    """Get all incomplete reminders from a list."""
    escaped_list = list_name.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set reminderNames to name of every reminder whose completed is false
            return reminderNames
        end tell
    end tell
    '''

    success, output = run_applescript(script)
    if not success:
        return {"items": []}

    if not output:
        return {"items": []}

    items = [name.strip() for name in output.split(',')]
    return {"items": items}


@app.delete("/reminder")
def delete_reminder(request: ReminderRequest):
    """Delete a reminder by exact text match."""
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

    success, output = run_applescript(script)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete reminder: {output}")
    return {"success": True}


@app.delete("/reminders/batch")
def delete_reminders_batch(request: BatchDeleteRequest):
    """Delete multiple reminders in a single AppleScript call.

    This batches deletions to avoid overwhelming the TCC daemon with
    repeated permission checks, which can cause Reminders to hang.
    """
    if not request.reminder_texts:
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

    success, output = run_applescript(script)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to batch delete reminders: {output}")
    return {"success": True}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("REMINDERS_PROXY_PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port)
