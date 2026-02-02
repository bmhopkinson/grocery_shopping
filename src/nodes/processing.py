"""
Recipe processing and user interaction nodes.

Handles URL processing, ingredient extraction, and user review interrupts.
"""

import json
from urllib.parse import urlparse
import logging

from bs4 import BeautifulSoup
from langgraph.types import interrupt

from models import (
    MealPlannerState,
    MealOption,
    ExtractedIngredients,
)
from prompts import get_extract_ingredients_prompt
from nodes.base import create_http_client, invoke_structured
from nodes.html_utils import extract_json_ld_recipe, extract_text_content
import ui


logger = logging.getLogger(__name__)


async def create_meal_from_url(state: MealPlannerState) -> dict:
    """
    Create a MealOption directly from a provided URL, skipping search.

    Fetches the page to extract the recipe title from JSON-LD or HTML.

    Reads: direct_url
    Writes: meal_options, selected_meal
    """
    url = state["direct_url"]

    ui.show_fetching_recipe(url)

    # Fetch the page to extract the recipe title
    title = "Recipe"  # Default fallback
    try:
        async with create_http_client(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

            # Try JSON-LD first for recipe name
            json_ld = extract_json_ld_recipe(html)
            if json_ld:
                data = json.loads(json_ld)
                if "name" in data:
                    title = data["name"]
            else:
                # Fall back to page title or h1
                soup = BeautifulSoup(html, "html.parser")
                title_tag = soup.find("title")
                if title_tag and title_tag.string:
                    title = title_tag.string.strip()
                else:
                    h1_tag = soup.find("h1")
                    if h1_tag:
                        title = h1_tag.get_text(strip=True)
    except Exception as e:
        ui.show_fetch_error(str(e))
        # Still create the meal option with a fallback title
        # extracted from the URL path
        path = urlparse(url).path
        path_parts = [p for p in path.split("/") if p]
        if path_parts:
            title = path_parts[-1].replace("-", " ").replace("_", " ").title()

    meal = MealOption(
        id=1,
        name=title,
        description="Direct URL entry",
        recipe_url=url
    )

    ui.show_user_selection(f"Using recipe: {title}")

    return {
        "meal_options": [meal],
        "selected_meal": meal  # Auto-select since it's the only option
    }


def present_options(state: MealPlannerState) -> dict:
    """
    Present meal options to user and wait for selection via interrupt.

    Reads: meal_options, cuisine_type
    Writes: selected_meal
    """
    meal_options = state["meal_options"]
    cuisine = state["cuisine_type"]

    options_text = ui.show_recipe_options(cuisine, meal_options)

    user_selection = interrupt(value={
        "prompt": options_text,
        "options": [opt.model_dump() for opt in meal_options],
        "instruction": "Enter a number 1-5 to select a recipe"
    })

    ui.show_user_selection(user_selection)

    try:
        selection_num = int(user_selection)
        if 1 <= selection_num <= len(meal_options):
            selected = meal_options[selection_num - 1]
        else:
            selected = meal_options[0]
    except (ValueError, TypeError):
        selected = meal_options[0]

    return {"selected_meal": selected}


async def extract_ingredients(state: MealPlannerState) -> dict:
    """
    Fetch the selected recipe page and extract ingredients using LLM.

    Reads: selected_meal
    Writes: grocery_list, error (on failure)
    """
    selected_meal = state["selected_meal"]

    logger.debug(f"extract_ingredients called with selected_meal: {selected_meal}")

    if not selected_meal:
        ui.show_no_recipe_url()
        return {"grocery_list": []}

    # Handle both MealOption objects and dicts (subgraph may serialize state)
    if isinstance(selected_meal, dict):
        recipe_url = selected_meal.get("recipe_url")
    else:
        recipe_url = selected_meal.recipe_url

    if not recipe_url:
        ui.show_no_recipe_url()
        return {"grocery_list": []}

    ui.show_fetching_recipe(recipe_url)

    try:
        async with create_http_client() as client:
            response = await client.get(recipe_url)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.debug(f"Fetch error: {e}")
        ui.show_fetch_error(str(e))
        error_msg = f"Failed to fetch recipe from {recipe_url}: {e}"
        return {"grocery_list": [], "error": error_msg}

    # Try JSON-LD structured data first (most reliable)
    json_ld = extract_json_ld_recipe(html)
    if json_ld:
        ui.show_found_structured_data()
        content = json_ld
    else:
        ui.show_extracting_text()
        content = extract_text_content(html)
        # Truncate if too long
        if len(content) > 30000:
            content = content[:30000]

    ui.show_extracting_ingredients()

    extract_prompt = get_extract_ingredients_prompt(content)
    result: ExtractedIngredients = invoke_structured(ExtractedIngredients, extract_prompt)

    ingredients = result.ingredients
    ui.show_extracted_count(len(ingredients))

    return {"grocery_list": ingredients}


def review_ingredients(state: MealPlannerState) -> dict:
    """
    Present ingredients for user review. User can approve or remove items.

    Reads: grocery_list
    Writes: grocery_list
    """
    ingredients = state.get("grocery_list", [])

    logger.debug(f"review_ingredients called with {len(ingredients) if ingredients else 0} ingredients")

    if not ingredients:
        ui.show_no_ingredients()
        return {"grocery_list": []}

    review_text = ui.show_ingredients_review(ingredients)

    # Handle both Ingredient objects and dicts
    ingredients_data = []
    for item in ingredients:
        if isinstance(item, dict):
            ingredients_data.append(item)
        else:
            ingredients_data.append(item.model_dump())

    user_input = interrupt(value={
        "prompt": review_text,
        "ingredients": ingredients_data,
        "instruction": "Enter 'ok' to approve or 'remove X, Y, Z' to remove items"
    })

    ui.show_user_input(user_input)

    # Parse user input
    user_input_str = str(user_input).strip().lower()

    # Accept "yes" as well as "ok" (frontend sends "yes")
    if user_input_str in ("ok", "yes", ""):
        return {"grocery_list": ingredients}

    # Handle "remove all" explicitly
    if user_input_str == "remove all":
        ui.show_removed_count(len(ingredients))
        return {"grocery_list": []}

    # Parse "remove: X, Y, Z" or "remove X, Y, Z" format
    # Frontend sends names like "remove: garlic, tomatoes"
    if user_input_str.startswith("remove"):
        # Strip "remove:" or "remove" prefix
        remove_part = user_input_str.replace("remove:", "").replace("remove", "").strip()

        # Collect indices and names to remove
        indices_to_remove = set()
        names_to_remove = set()

        for part in remove_part.replace(",", " ").split():
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                indices_to_remove.add(int(part))
            else:
                names_to_remove.add(part.lower())

        # Filter by indices OR names
        def should_keep(idx, item):
            # Check index (1-indexed)
            if idx in indices_to_remove:
                return False
            # Check name (case-insensitive)
            item_name = item.name if hasattr(item, 'name') else item.get('name', '')
            if item_name.lower() in names_to_remove:
                return False
            return True

        filtered = [
            item for i, item in enumerate(ingredients, 1)
            if should_keep(i, item)
        ]
        ui.show_removed_count(len(ingredients) - len(filtered))
        return {"grocery_list": filtered}

    # If we couldn't parse, keep original list
    return {"grocery_list": ingredients}
