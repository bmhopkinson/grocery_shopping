"""
Graph execution streaming for the meal planner SSE stream.
"""

import logging
from typing import AsyncGenerator, Optional

from langgraph.types import Command

from server.sessions import Session
from server.sse import (
    sse_event,
    error_event,
    complete_event,
    grocery_list_event,
    status_event,
)
from server.interrupts import detect_interrupt


logger = logging.getLogger(__name__)


NODE_MESSAGES = {
    "create_meal_from_url": "Fetching recipe from URL...",
    "search_meals": "Searching for recipes...",
    "parse_meals": "Analyzing search results...",
    "validate_recipes": "Validating recipe URLs...",
    "refine_search": "Refining search with specific dishes...",
    "present_options": "Preparing meal options...",
    "extract_ingredients": "Extracting ingredients from recipe...",
    "review_ingredients": "Preparing ingredient list for review...",
    "add_to_reminders": "Adding items to reminders...",
}


def _build_invoke_input(initial_input: Optional[dict], resume_input: Optional[str]):
    if resume_input is not None:
        return Command(resume=resume_input)
    if initial_input is not None:
        return initial_input
    raise ValueError("Must provide either initial_input or resume_input")


def _extract_status_event(event: dict) -> Optional[dict]:
    if event.get("event") == "on_chain_start":
        node_name = event.get("name")
        if node_name in NODE_MESSAGES:
            return status_event(node_name, NODE_MESSAGES[node_name])
    return None


def _handle_interrupt(state) -> dict:
    interrupt_value = None
    if state.tasks and state.tasks[0].interrupts:
        interrupt_value = state.tasks[0].interrupts[0].value

    next_node = state.next[0] if state.next else None
    match = detect_interrupt(next_node, interrupt_value)
    return sse_event(match.event_name, match.event_data)


async def _handle_completion(session: Session, state) -> AsyncGenerator[dict, None]:
    session.completed = True
    values = state.values

    error = values.get("error")
    if error:
        yield error_event(error)
        return

    selected_meal = values.get("selected_meal")
    grocery_list = values.get("grocery_list", [])
    reminders_added = values.get("reminders_added", False)

    if grocery_list:
        yield grocery_list_event(grocery_list)

    yield complete_event(selected_meal, grocery_list, reminders_added)


async def stream_graph_execution(
    session: Session,
    initial_input: Optional[dict] = None,
    resume_input: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """Stream graph execution as SSE events until completion or interrupt."""
    config = {"configurable": {"thread_id": session.thread_id}}
    graph = session.graph

    logger.info(f"stream_graph_execution started for session {session.session_id}")

    try:
        invoke_input = _build_invoke_input(initial_input, resume_input)

        async for event in graph.astream_events(invoke_input, config=config, version="v2"):
            status = _extract_status_event(event)
            if status:
                yield status

        state = await graph.aget_state(config)
        session.last_state = state

        if state.next:
            logger.info(f"Session {session.session_id} - interrupt at node(s): {list(state.next)}")
            yield _handle_interrupt(state)
        else:
            logger.info(f"Session {session.session_id} - graph completed")
            async for event in _handle_completion(session, state):
                yield event

    except Exception as e:
        logger.exception(f"Session {session.session_id} - error in stream_graph_execution: {e}")
        yield error_event(str(e))
