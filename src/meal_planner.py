"""
Meal Planning Agent using LangGraph with Interrupts

Workflow:
1. User inputs desired meal type (e.g., "mexican")
2. Agent searches web to find potential recipes
3. Parse search results to extract recipe names and URLs
4. Validate that URLs point to single recipes (not collections)
   - If too few valid recipes, refine search with specific dish names
5. Presents validated recipe options to user via interrupt (human-in-the-loop)
6. User selects a recipe; selected_meal contains recipe_url for next steps
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from langgraph.graph import START, END, StateGraph
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from models import MealPlannerState


# Module-level connection pool (singleton)
_connection_pool: AsyncConnectionPool | None = None
_checkpointer_instance: AsyncPostgresSaver | None = None


async def get_checkpointer_async():
    """Get the async checkpointer - AsyncPostgresSaver if DATABASE_URL is set, otherwise MemorySaver."""
    global _connection_pool, _checkpointer_instance

    # Return cached instance if available
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    database_url = os.environ.get("DATABASE_URL")

    print(f"[DEBUG] get_checkpointer_async called, DATABASE_URL={'set' if database_url else 'not set'}")

    if not database_url:
        print("[DEBUG] Using MemorySaver (no DATABASE_URL)")
        _checkpointer_instance = MemorySaver()
        return _checkpointer_instance

    print(f"[DEBUG] Connecting to PostgreSQL: {database_url.replace('mealplanner:mealplanner', 'mealplanner:***')}")

    if _connection_pool is None:
        try:
            print("[DEBUG] Creating async connection pool...")
            _connection_pool = AsyncConnectionPool(
                conninfo=database_url,
                max_size=20,
                open=False,
                kwargs={"autocommit": True, "prepare_threshold": 0}
            )
            await _connection_pool.open()
            print("[DEBUG] Async connection pool created and opened successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create async connection pool: {e}")
            raise

    try:
        print("[DEBUG] Creating AsyncPostgresSaver...")
        checkpointer = AsyncPostgresSaver(_connection_pool)
        print("[DEBUG] Running checkpointer.setup()...")
        await checkpointer.setup()
        print("[DEBUG] AsyncPostgresSaver ready")
        _checkpointer_instance = checkpointer
        return checkpointer
    except Exception as e:
        print(f"[ERROR] Failed to setup AsyncPostgresSaver: {e}")
        raise


def get_checkpointer():
    """Sync wrapper - returns None, caller must use get_checkpointer_async()."""
    # For backwards compatibility with CLI mode, return MemorySaver if no DATABASE_URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return MemorySaver()
    # Return None to signal that async initialization is needed
    return None


from nodes import (
    search_meals,
    parse_meals,
    validate_recipes,
    refine_search,
    should_refine,
    route_by_input,
    create_meal_from_url,
    present_options,
    extract_ingredients,
    review_ingredients,
    add_to_reminders,
)


def build_meal_processing_subgraph() -> StateGraph:
    """Build the subgraph for processing a single selected meal.

    This subgraph handles:
    - Fetching recipe and extracting ingredients
    - User review of ingredients
    - Adding to Apple Reminders
    """
    builder = StateGraph(MealPlannerState)

    builder.add_node("extract_ingredients", extract_ingredients)
    builder.add_node("review_ingredients", review_ingredients)
    builder.add_node("add_to_reminders", add_to_reminders)

    builder.add_edge(START, "extract_ingredients")
    builder.add_edge("extract_ingredients", "review_ingredients")
    builder.add_edge("review_ingredients", "add_to_reminders")
    builder.add_edge("add_to_reminders", END)

    return builder.compile()


def build_meal_planner_graph(checkpointer=None) -> StateGraph:
    """Build the meal planner graph with multiple entry points.

    Supports two entry modes:
    - Search mode: User provides cuisine_type, searches for recipes
    - URL mode: User provides direct_url, skips directly to processing
    """
    builder = StateGraph(MealPlannerState)

    # Search flow nodes
    builder.add_node("search_meals", search_meals)
    builder.add_node("parse_meals", parse_meals)
    builder.add_node("validate_recipes", validate_recipes)
    builder.add_node("refine_search", refine_search)
    builder.add_node("present_options", present_options)

    # Direct URL node
    builder.add_node("create_meal_from_url", create_meal_from_url)

    # Add subgraph as a node for processing the selected meal
    builder.add_node("process_meal", build_meal_processing_subgraph())

    # Entry routing: direct URL vs search
    builder.add_conditional_edges(START, route_by_input)

    # Search flow edges
    builder.add_edge("search_meals", "parse_meals")
    builder.add_edge("parse_meals", "validate_recipes")
    builder.add_conditional_edges("validate_recipes", should_refine)
    builder.add_edge("refine_search", "validate_recipes")
    builder.add_edge("present_options", "process_meal")

    # Direct URL flow
    builder.add_edge("create_meal_from_url", "process_meal")

    # Subgraph to END
    builder.add_edge("process_meal", END)

    if checkpointer is None:
        checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer)


async def run_meal_planner(cuisine_type: str = "", direct_url: str = ""):
    """Run the meal planner with a given cuisine type or direct recipe URL.

    Args:
        cuisine_type: Type of cuisine to search for (e.g., "mexican", "italian")
        direct_url: Direct URL to a recipe page (skips search if provided)
    """
    graph = build_meal_planner_graph()

    initial_state = {
        "direct_url": direct_url if direct_url else None,
        "cuisine_type": cuisine_type,
        "preferred_sources": [],  # Empty = search all sites when using CLI
        "search_results": None,
        "meal_options": None,
        "selected_meal": None,
        "messages": [],
        "refinement_count": 0,
        "refine_dishes": None,
        "grocery_list": None,
        "reminders_added": None
    }

    config = {"configurable": {"thread_id": "meal-planner-1"}}

    print(f"\n{'='*60}")
    if direct_url:
        print(f"🍴 Starting Meal Planner with URL: {direct_url}")
    else:
        print(f"🍴 Starting Meal Planner for: {cuisine_type}")
    print(f"{'='*60}\n")

    result = await graph.ainvoke(initial_state, config=config)

    # Handle interrupts in a loop (meal selection, ingredient review, etc.)
    while True:
        state = graph.get_state(config)

        if not state.next:
            break

        interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else None

        if interrupt_value:
            print("\n" + interrupt_value.get("prompt", ""))
            user_input = input("\n> ")

            result = await graph.ainvoke(
                Command(resume=user_input),
                config=config
            )
        else:
            break

    selected = result.get('selected_meal')
    grocery_list = result.get('grocery_list', [])
    reminders_added = result.get('reminders_added', False)

    print(f"\n{'='*60}")
    print(f"✅ Selected recipe: {selected.name if selected else 'None'}")
    print(f"   {selected.description if selected else ''}")
    if selected and selected.recipe_url:
        print(f"   🔗 Recipe URL: {selected.recipe_url}")
    print(f"{'='*60}")

    if grocery_list:
        print(f"\n🛒 Grocery List ({len(grocery_list)} items):")
        print("-" * 40)
        for item in grocery_list:
            if item.unit:
                print(f"  • {item.amount} {item.unit} {item.name}")
            else:
                print(f"  • {item.amount} {item.name}")
        print("-" * 40)

        if reminders_added:
            print("\n✅ Items have been added to Apple Reminders (Groceries list)")
        else:
            print("\n⏭️  Items were not added to Apple Reminders")

    print()
    return result


def main():
    """Interactive main function."""
    print("\n🍽️  Welcome to the Meal Planner!")
    print("-" * 40)

    user_input = input("Enter a cuisine type (e.g., mexican) or a recipe URL: ").strip()

    if not user_input:
        user_input = "mexican"
        print(f"Using default: {user_input}")

    # Detect if input is a URL or cuisine type
    if user_input.startswith(("http://", "https://")):
        result = asyncio.run(run_meal_planner(direct_url=user_input))
    else:
        result = asyncio.run(run_meal_planner(cuisine_type=user_input))

    return result


if __name__ == "__main__":
    main()
