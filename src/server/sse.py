"""
SSE (Server-Sent Events) utilities.

Provides factory functions for creating SSE events and serialization helpers.
"""

import json
from typing import Any


def sse_event(event_type: str, data: dict) -> dict:
    """
    Format an SSE event for sse-starlette.

    Args:
        event_type: The event type name (e.g., "status", "complete")
        data: The event payload as a dictionary

    Returns:
        Dict formatted for sse-starlette EventSourceResponse
    """
    return {
        "event": event_type,
        "data": json.dumps(data)
    }


def serialize_model(obj: Any) -> Any:
    """
    Serialize a Pydantic model or list of models to dict.

    Handles:
    - None values
    - Single Pydantic models with model_dump()
    - Lists of Pydantic models
    - Already-serialized dicts (passthrough)

    Args:
        obj: Object to serialize

    Returns:
        Serialized dict, list of dicts, or original value if not a model
    """
    if obj is None:
        return None

    # Handle single Pydantic model
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()

    # Handle list of Pydantic models
    if isinstance(obj, list) and obj and hasattr(obj[0], 'model_dump'):
        return [item.model_dump() for item in obj]

    # Already a dict or primitive
    return obj


# Pre-defined event constructors for type safety and consistency


def session_start_event(session_id: str) -> dict:
    """Create a session_start SSE event."""
    return sse_event("session_start", {"session_id": session_id})


def status_event(node: str, message: str) -> dict:
    """Create a status SSE event for node progress updates."""
    return sse_event("status", {"node": node, "message": message})


def error_event(message: str) -> dict:
    """Create an error SSE event."""
    return sse_event("error", {"message": message})


def complete_event(selected_meal: Any, grocery_list: list, reminders_added: bool) -> dict:
    """
    Create a completion SSE event.

    Args:
        selected_meal: The selected MealOption (model or dict)
        grocery_list: List of Ingredient models or dicts
        reminders_added: Whether items were added to reminders
    """
    return sse_event("complete", {
        "selected_meal": serialize_model(selected_meal),
        "grocery_list": serialize_model(grocery_list) or [],
        "reminders_added": reminders_added
    })


def grocery_list_event(items: list) -> dict:
    """Create a grocery_list SSE event with the list of items."""
    return sse_event("grocery_list", {
        "items": serialize_model(items)
    })
