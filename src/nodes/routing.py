"""
Routing functions for conditional graph edges.

These functions determine which path the graph takes based on state.
"""

from models import MealPlannerState


def should_refine(state: MealPlannerState) -> str:
    """
    Determine if we need to refine the search or proceed to presentation.

    Returns:
        "refine_search" if more recipes are needed, "present_options" otherwise
    """
    if state.get("refine_dishes"):
        return "refine_search"
    return "present_options"


def route_by_input(state: MealPlannerState) -> str:
    """
    Route based on whether a direct_url is provided or we need to search.

    Returns:
        "create_meal_from_url" if direct_url provided, "search_meals" otherwise
    """
    direct_url = state.get("direct_url")
    if direct_url and direct_url.startswith(("http://", "https://")):
        return "create_meal_from_url"
    return "search_meals"
