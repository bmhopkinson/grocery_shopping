"""
Recipe Extractor Agent using LangGraph

Workflow:
1. Fetch the recipe page HTML
2. Extract metadata (name, creator, description)
3. Extract ingredients
4. Extract step-by-step directions
5. Save everything to the database as a new recipe
"""

from langgraph.graph import START, END, StateGraph

from agent.models import RecipeExtractorState
from agent.nodes.recipe_extractor import (
    fetch_recipe_page,
    extract_recipe_metadata,
    extract_recipe_ingredients_for_db,
    extract_recipe_directions,
    save_recipe_to_db,
)


EXTRACTOR_NODE_MESSAGES = {
    "fetch_recipe_page": "Fetching recipe page...",
    "extract_metadata": "Extracting recipe details...",
    "extract_ingredients": "Extracting ingredients...",
    "extract_directions": "Extracting cooking directions...",
    "save_recipe": "Saving recipe to library...",
}


def _route_after_fetch(state: RecipeExtractorState) -> str:
    return END if state.get("error") else "extract_metadata"


def build_recipe_extractor_graph() -> StateGraph:
    """Build the recipe extractor graph. No checkpointer needed (no interrupts)."""
    builder = StateGraph(RecipeExtractorState)

    builder.add_node("fetch_recipe_page", fetch_recipe_page)
    builder.add_node("extract_metadata", extract_recipe_metadata)
    builder.add_node("extract_ingredients", extract_recipe_ingredients_for_db)
    builder.add_node("extract_directions", extract_recipe_directions)
    builder.add_node("save_recipe", save_recipe_to_db)

    builder.add_edge(START, "fetch_recipe_page")
    builder.add_conditional_edges("fetch_recipe_page", _route_after_fetch)
    builder.add_edge("extract_metadata", "extract_ingredients")
    builder.add_edge("extract_ingredients", "extract_directions")
    builder.add_edge("extract_directions", "save_recipe")
    builder.add_edge("save_recipe", END)

    return builder.compile()
