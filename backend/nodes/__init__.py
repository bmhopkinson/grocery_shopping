"""
Graph node implementations for the Meal Planner agent.

This package contains all node functions organized by workflow stage:
- routing: Conditional edge functions for graph routing
- search: Recipe search and validation nodes
- processing: Recipe processing and user interaction nodes
- reminders_node: Apple Reminders integration

All node functions are re-exported here for backward compatibility.
"""

# Re-export all nodes for backward compatibility with:
#   from nodes import search_meals, parse_meals, ...

from nodes.routing import (
    should_refine,
    route_by_input,
)

from nodes.search import (
    search_meals,
    parse_meals,
    validate_recipes,
    refine_search,
)

from nodes.processing import (
    create_meal_from_url,
    present_options,
    extract_ingredients,
    review_ingredients,
)

from nodes.reminders_node import (
    add_to_reminders,
)


__all__ = [
    # Routing
    "should_refine",
    "route_by_input",
    # Search
    "search_meals",
    "parse_meals",
    "validate_recipes",
    "refine_search",
    # Processing
    "create_meal_from_url",
    "present_options",
    "extract_ingredients",
    "review_ingredients",
    # Reminders
    "add_to_reminders",
]
