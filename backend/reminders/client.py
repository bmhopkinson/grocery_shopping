"""
Apple Reminders integration.

Supports two modes:
- Direct EventKit via PyObjC (when running on macOS)
- HTTP proxy (when running in Docker, set REMINDERS_PROXY_URL env var)
"""

import os

import httpx

# Check for proxy mode
PROXY_URL = os.getenv("REMINDERS_PROXY_URL")


def _use_proxy() -> bool:
    """Check if we should use the HTTP proxy."""
    return PROXY_URL is not None


def _get_store():
    """Lazily import and return the module-level EventKit store singleton."""
    from reminders.eventkit_store import _store
    return _store


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

    ok, _ = _get_store().create_reminder(list_name, reminder_text)
    return ok


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

    ok, result = _get_store().list_exists(list_name)
    return result if ok else False


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

    ok, _ = _get_store().create_list(list_name)
    return ok


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

    ok, result = _get_store().get_all_lists()
    return result if ok else []


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

    ok, result = _get_store().get_list_items(list_name)
    return result if ok else []


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

    ok, _ = _get_store().delete_reminder(list_name, reminder_text)
    return ok


def delete_reminders_batch(list_name: str, reminder_texts: list[str]) -> bool:
    """
    Delete multiple reminders in a single batched EventKit commit.

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

    ok, _ = _get_store().delete_reminders_batch(list_name, reminder_texts)
    return ok
