"""
Server components for the Meal Planner API.

This package contains:
- sse: SSE event factory and serialization utilities
- interrupts: Interrupt type registry and handlers
"""

from server.sse import (
    sse_event,
    serialize_model,
    session_start_event,
    status_event,
    error_event,
    complete_event,
    grocery_list_event,
)

from server.interrupts import (
    InterruptType,
    InterruptMatch,
    detect_interrupt,
)


__all__ = [
    # SSE utilities
    "sse_event",
    "serialize_model",
    "session_start_event",
    "status_event",
    "error_event",
    "complete_event",
    "grocery_list_event",
    # Interrupt handling
    "InterruptType",
    "InterruptMatch",
    "detect_interrupt",
]
