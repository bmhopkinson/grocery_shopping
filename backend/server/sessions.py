"""
Session management for active meal planning sessions.
"""

from agent.meal_planner import build_meal_planner_graph


class Session:
    """Holds state for an active meal planning session."""

    def __init__(
        self,
        session_id: str,
        cuisine_type: str = "",
        direct_url: str = "",
        preferred_sources: list[str] = None,
        checkpointer=None,
    ):
        self.session_id = session_id
        self.cuisine_type = cuisine_type
        self.direct_url = direct_url
        self.preferred_sources = preferred_sources or []
        self.thread_id = f"session-{session_id}"
        self.graph = build_meal_planner_graph(checkpointer=checkpointer)
        self.started = False
        self.completed = False
        self.last_state = None


# In-memory session store (use Redis for production)
sessions: dict[str, Session] = {}
