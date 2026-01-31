"""
Apple Reminders integration.

Supports two modes:
- Direct AppleScript (when running on macOS)
- HTTP proxy (when running in Docker, set REMINDERS_PROXY_URL env var)
"""

import os
import subprocess

import httpx

# Check for proxy mode
PROXY_URL = os.getenv("REMINDERS_PROXY_URL")


def _use_proxy() -> bool:
    """Check if we should use the HTTP proxy."""
    return PROXY_URL is not None


def create_reminder(list_name: str, reminder_text: str) -> bool:
    """
    Create a reminder in the specified list.

    Args:
        list_name: Name of the Reminders list
        reminder_text: Text content of the reminder

    Returns:
        bool: True if successful, False otherwise
    """
    if _use_proxy():
        try:
            response = httpx.post(
                f"{PROXY_URL}/reminder",
                json={"list_name": list_name, "reminder_text": reminder_text},
                timeout=10.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error creating reminder via proxy: {e}")
            return False

    escaped_text = reminder_text.replace('"', '\\"').replace('\\', '\\\\')

    applescript = f'''
    tell application "Reminders"
        tell list "{list_name}"
            make new reminder with properties {{name:"{escaped_text}"}}
        end tell
    end tell
    '''

    try:
        subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating reminder: {e.stderr}")
        return False


def list_exists(list_name: str) -> bool:
    """
    Check if a Reminders list exists.

    Args:
        list_name: Name of the list to check

    Returns:
        bool: True if list exists, False otherwise
    """
    if _use_proxy():
        try:
            response = httpx.get(
                f"{PROXY_URL}/lists/{list_name}/exists",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json().get("exists", False)
            return False
        except Exception:
            return False

    applescript = f'''
    tell application "Reminders"
        set listNames to name of every list
        return listNames contains "{list_name}"
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == "true"
    except subprocess.CalledProcessError:
        return False


def create_list(list_name: str) -> bool:
    """
    Create a new Reminders list.

    Args:
        list_name: Name of the list to create

    Returns:
        bool: True if successful, False otherwise
    """
    if _use_proxy():
        try:
            response = httpx.post(
                f"{PROXY_URL}/lists",
                json={"list_name": list_name},
                timeout=10.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error creating list via proxy: {e}")
            return False

    applescript = f'''
    tell application "Reminders"
        make new list with properties {{name:"{list_name}"}}
    end tell
    '''

    try:
        subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating list: {e.stderr}")
        return False


def get_all_lists() -> list[str]:
    """
    Get all Reminders lists.

    Returns:
        list[str]: List of reminder list names
    """
    if _use_proxy():
        try:
            response = httpx.get(f"{PROXY_URL}/lists", timeout=10.0)
            if response.status_code == 200:
                return response.json().get("lists", [])
            return []
        except Exception:
            return []

    applescript = '''
    tell application "Reminders"
        set listNames to name of every list
        return listNames
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True
        )
        lists_str = result.stdout.strip()
        if not lists_str:
            return []
        return [name.strip() for name in lists_str.split(',')]
    except subprocess.CalledProcessError:
        return []


def get_reminders(list_name: str) -> list[str]:
    """
    Get all incomplete reminder texts from a list.

    Args:
        list_name: Name of the Reminders list

    Returns:
        list[str]: List of reminder texts (names)
    """
    if _use_proxy():
        try:
            response = httpx.get(
                f"{PROXY_URL}/lists/{list_name}/items",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json().get("items", [])
            return []
        except Exception:
            return []

    escaped_list = list_name.replace('"', '\\"')
    applescript = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set reminderNames to name of every reminder whose completed is false
            return reminderNames
        end tell
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True
        )
        reminders_str = result.stdout.strip()
        if not reminders_str:
            return []
        return [name.strip() for name in reminders_str.split(',')]
    except subprocess.CalledProcessError:
        return []


def delete_reminder(list_name: str, reminder_text: str) -> bool:
    """
    Delete a reminder by exact text match.

    Args:
        list_name: Name of the Reminders list
        reminder_text: Exact text of the reminder to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if _use_proxy():
        try:
            response = httpx.request(
                "DELETE",
                f"{PROXY_URL}/reminder",
                json={"list_name": list_name, "reminder_text": reminder_text},
                timeout=10.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error deleting reminder via proxy: {e}")
            return False

    escaped_text = reminder_text.replace('"', '\\"').replace('\\', '\\\\')
    escaped_list = list_name.replace('"', '\\"')

    applescript = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set targetReminders to every reminder whose name is "{escaped_text}"
            repeat with r in targetReminders
                delete r
            end repeat
        end tell
    end tell
    '''

    try:
        subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error deleting reminder: {e.stderr}")
        return False


def delete_reminders_batch(list_name: str, reminder_texts: list[str]) -> bool:
    """
    Delete multiple reminders in a single AppleScript call.

    This batches deletions to avoid overwhelming the TCC daemon with
    repeated permission checks, which can cause Reminders to hang.

    Args:
        list_name: Name of the Reminders list
        reminder_texts: List of exact reminder texts to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if not reminder_texts:
        return True

    if _use_proxy():
        try:
            response = httpx.request(
                "DELETE",
                f"{PROXY_URL}/reminders/batch",
                json={"list_name": list_name, "reminder_texts": reminder_texts},
                timeout=30.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error batch deleting reminders via proxy: {e}")
            return False

    escaped_list = list_name.replace('"', '\\"')

    # Build AppleScript list of names to delete
    escaped_names = [text.replace('\\', '\\\\').replace('"', '\\"') for text in reminder_texts]
    names_list = ', '.join(f'"{name}"' for name in escaped_names)

    applescript = f'''
    tell application "Reminders"
        tell list "{escaped_list}"
            set namesToDelete to {{{names_list}}}
            repeat with nameToDelete in namesToDelete
                set targetReminders to every reminder whose name is nameToDelete
                repeat with r in targetReminders
                    delete r
                end repeat
            end repeat
        end tell
    end tell
    '''

    try:
        subprocess.run(
            ['osascript', '-e', applescript],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error batch deleting reminders: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("Error: Batch delete timed out")
        return False
