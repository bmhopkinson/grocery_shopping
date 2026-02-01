"""
Graph node functions for the Meal Planner agent.
"""

import json
import re
import sys
from pathlib import Path
from typing import List

# Add src directory to Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from bs4 import BeautifulSoup

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchResults
from langgraph.types import interrupt

import httpx

from reminders import create_reminder, list_exists, create_list, get_all_lists, get_reminders, delete_reminders_batch
from collate import collate_ingredients
import ui

from models import (
    MealPlannerState,
    MealOption,
    ParsedRecipes,
    ValidationResult,
    DishNames,
    Ingredient,
    ExtractedIngredients,
)
from prompts import (
    get_parse_recipes_prompt,
    get_validate_recipes_prompt,
    get_dish_names_prompt,
    get_refine_search_prompt,
    get_refine_search_query,
    get_extract_ingredients_prompt,
)


# Initialize tools and LLM
search_tool = DuckDuckGoSearchResults(max_results=10)
llm = ChatOpenAI(model="gpt-5.2", temperature=0)


def search_meals(state: MealPlannerState) -> dict:
    """Search the web for meal ideas and recipe links based on cuisine type."""
    cuisine = state["cuisine_type"]
    ui.show_searching(cuisine)

    query = f"{cuisine} dinner recipe with ingredients"
    results = search_tool.invoke(query)

    ui.show_search_complete()
    return {"search_results": results}


def parse_meals(state: MealPlannerState) -> dict:
    """Use LLM to parse search results into structured meal options with recipe URLs."""
    search_results = state["search_results"]
    cuisine = state["cuisine_type"]

    ui.show_parsing()

    structured_llm = llm.with_structured_output(ParsedRecipes)
    parse_prompt = get_parse_recipes_prompt(cuisine, search_results)
    result: ParsedRecipes = structured_llm.invoke([HumanMessage(content=parse_prompt)])

    meal_options = [
        MealOption(
            id=i,
            name=recipe.name,
            description=recipe.description,
            recipe_url=recipe.url
        )
        for i, recipe in enumerate(result.recipes[:5], 1)
    ]

    display_text = "\n".join([
        f"{opt.id}. **{opt.name}**: {opt.description}"
        for opt in meal_options
    ])

    ui.show_parsed_count(len(meal_options))
    return {
        "meal_options": meal_options,
        "messages": [AIMessage(content=display_text)]
    }


def validate_recipes(state: MealPlannerState) -> dict:
    """Validate that recipe URLs point to single recipes, not collections. Refine if needed."""
    meal_options = state["meal_options"]
    cuisine = state["cuisine_type"]
    refinement_count = state.get("refinement_count", 0)

    ui.show_validating(refinement_count + 1)

    structured_llm = llm.with_structured_output(ValidationResult)

    recipes_text = "\n".join([
        f"- {opt.name}: {opt.description} (URL: {opt.recipe_url})"
        for opt in meal_options
    ])

    validate_prompt = get_validate_recipes_prompt(recipes_text, cuisine)
    result: ValidationResult = structured_llm.invoke([HumanMessage(content=validate_prompt)])

    valid_recipes = [
        MealOption(
            id=i,
            name=recipe.name,
            description=recipe.description,
            recipe_url=recipe.url
        )
        for i, recipe in enumerate(result.valid_recipes[:5], 1)
    ]
    dish_names = result.dish_names

    ui.show_valid_count(len(valid_recipes))

    if len(valid_recipes) >= 3:
        return {"meal_options": valid_recipes}

    if refinement_count < 2 and dish_names:
        ui.show_refining()
        return {
            "meal_options": valid_recipes,
            "refinement_count": refinement_count + 1,
            "refine_dishes": dish_names[:5]
        }

    return {"meal_options": valid_recipes if valid_recipes else meal_options}


def refine_search(state: MealPlannerState) -> dict:
    """Search for specific dish names to get direct recipe links."""
    cuisine = state["cuisine_type"]
    sources = state.get("preferred_sources", [])
    dish_names = state.get("refine_dishes", [])
    existing_valid = state.get("meal_options", [])

    if not dish_names:
        structured_llm = llm.with_structured_output(DishNames)
        dish_prompt = get_dish_names_prompt(cuisine)
        result: DishNames = structured_llm.invoke([HumanMessage(content=dish_prompt)])
        dish_names = result.dishes[:5]

    ui.show_searching_dishes(dish_names)

    all_results = []
    for dish in dish_names[:5]:
        query = get_refine_search_query(dish, sources)
        results = search_tool.invoke(query)
        all_results.append(f"--- {dish} ---\n{results}")

    combined_results = "\n\n".join(all_results)

    structured_llm = llm.with_structured_output(ParsedRecipes)
    parse_prompt = get_refine_search_prompt(combined_results, sources)
    result: ParsedRecipes = structured_llm.invoke([HumanMessage(content=parse_prompt)])

    all_recipes = existing_valid + [
        MealOption(
            id=0,
            name=recipe.name,
            description=recipe.description,
            recipe_url=recipe.url
        )
        for recipe in result.recipes
    ]

    seen_urls = set()
    unique_recipes: List[MealOption] = []
    for r in all_recipes:
        if r.recipe_url and r.recipe_url not in seen_urls:
            seen_urls.add(r.recipe_url)
            unique_recipes.append(r)

    unique_recipes = [
        MealOption(id=i, name=r.name, description=r.description, recipe_url=r.recipe_url)
        for i, r in enumerate(unique_recipes[:5], 1)
    ]

    ui.show_refinement_complete(len(unique_recipes))
    return {
        "meal_options": unique_recipes[:5],
        "search_results": combined_results,
        "refine_dishes": None
    }


def should_refine(state: MealPlannerState) -> str:
    """Determine if we need to refine the search or proceed to presentation."""
    if state.get("refine_dishes"):
        return "refine_search"
    return "present_options"


def route_by_input(state: MealPlannerState) -> str:
    """Route based on whether a direct_url is provided or we need to search."""
    direct_url = state.get("direct_url")
    if direct_url and direct_url.startswith(("http://", "https://")):
        return "create_meal_from_url"
    return "search_meals"


async def create_meal_from_url(state: MealPlannerState) -> dict:
    """Create a MealOption directly from a provided URL, skipping search."""
    url = state["direct_url"]

    ui.show_fetching_recipe(url)

    # Fetch the page to extract the recipe title
    title = "Recipe"  # Default fallback
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
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
        from urllib.parse import urlparse
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
    """Present meal options with recipe links to user and wait for selection via interrupt."""
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


def extract_json_ld_recipe(html: str) -> str | None:
    """Extract recipe data from JSON-LD structured data if present."""
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)

            # Handle both single objects and arrays
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Recipe":
                        return json.dumps(item, indent=2)
            elif isinstance(data, dict):
                if data.get("@type") == "Recipe":
                    return json.dumps(data, indent=2)
                # Check @graph array
                if "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") == "Recipe":
                            return json.dumps(item, indent=2)
        except (json.JSONDecodeError, TypeError):
            continue

    return None


def extract_text_content(html: str) -> str:
    """Extract clean text content from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "header", "footer"]):
        element.decompose()

    text = soup.get_text(separator="\n")
    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


async def extract_ingredients(state: MealPlannerState) -> dict:
    """Fetch the selected recipe page and extract ingredients."""
    selected_meal = state["selected_meal"]

    # Debug logging
    print(f"[DEBUG] extract_ingredients called")
    print(f"[DEBUG] selected_meal type: {type(selected_meal)}")
    print(f"[DEBUG] selected_meal value: {selected_meal}")

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=headers) as client:
            response = await client.get(recipe_url)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        print(f"[DEBUG] Fetch error: {e}")
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

    structured_llm = llm.with_structured_output(ExtractedIngredients)
    extract_prompt = get_extract_ingredients_prompt(content)
    result: ExtractedIngredients = structured_llm.invoke([HumanMessage(content=extract_prompt)])

    ingredients = result.ingredients
    ui.show_extracted_count(len(ingredients))

    return {"grocery_list": ingredients}


def review_ingredients(state: MealPlannerState) -> dict:
    """Present ingredients for user review. User can approve or remove items."""
    ingredients = state.get("grocery_list", [])

    print(f"[DEBUG] review_ingredients called")
    print(f"[DEBUG] grocery_list length: {len(ingredients) if ingredients else 0}")
    if ingredients:
        print(f"[DEBUG] first ingredient type: {type(ingredients[0])}")

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
    user_input = str(user_input).strip().lower()

    if user_input == "ok" or user_input == "":
        return {"grocery_list": ingredients}

    # Parse "remove X, Y, Z" format
    if user_input.startswith("remove"):
        remove_part = user_input.replace("remove", "").strip()
        try:
            # Extract numbers from the input
            indices_to_remove = set()
            for part in remove_part.replace(",", " ").split():
                if part.isdigit():
                    indices_to_remove.add(int(part))

            # Filter out removed items (1-indexed)
            filtered = [
                item for i, item in enumerate(ingredients, 1)
                if i not in indices_to_remove
            ]
            ui.show_removed_count(len(ingredients) - len(filtered))
            return {"grocery_list": filtered}
        except (ValueError, IndexError):
            pass

    # If we couldn't parse, keep original list
    return {"grocery_list": ingredients}


def add_to_reminders(state: MealPlannerState) -> dict:
    """Present final grocery list for approval and add to Apple Reminders."""
    ingredients = state.get("grocery_list", [])

    if not ingredients:
        ui.show_no_ingredients_for_reminders()
        return {"reminders_added": False}

    # Build item list for frontend display
    items_for_display = [
        {"name": item.name, "amount": item.amount, "unit": item.unit or ""}
        for item in ingredients
    ]

    # Get existing reminder lists
    existing_lists = get_all_lists()

    list_input = interrupt(value={
        "existing_lists": existing_lists,
        "items": items_for_display,
        "instruction": "Enter list number, new list name, or 'skip'"
    })

    ui.show_user_input(list_input)

    list_input = str(list_input).strip()

    if list_input.lower() in ("skip", "no", "cancel", ""):
        ui.show_skipping_reminders()
        return {"reminders_added": False}

    # Determine list name
    if list_input.isdigit():
        idx = int(list_input) - 1
        if 0 <= idx < len(existing_lists):
            list_name = existing_lists[idx]
        else:
            list_name = list_input  # Use as literal name if out of range
    else:
        list_name = list_input

    # Ensure list exists
    is_new_list = not list_exists(list_name)
    if is_new_list:
        ui.show_creating_list(list_name)
        if not create_list(list_name):
            ui.show_list_creation_failed(list_name)
            return {"reminders_added": False}

    # Read existing items and collate with new ingredients
    existing_items = [] if is_new_list else get_reminders(list_name)
    items_to_add, items_to_update = collate_ingredients(existing_items, ingredients)

    success_count = 0
    updated_count = 0
    failed_items = []

    total_items = len(items_to_add) + len(items_to_update)
    ui.show_adding_items(total_items, list_name, updated=len(items_to_update))

    # Handle updates: batch delete old items first, then add combined
    if items_to_update:
        old_texts = [old_text for old_text, _ in items_to_update]
        delete_reminders_batch(list_name, old_texts)

    # Add combined reminders for updated items
    for old_text, combined in items_to_update:
        if combined.unit:
            item_text = f"{combined.name} ({combined.amount} {combined.unit})"
        else:
            item_text = f"{combined.name} ({combined.amount})"

        if create_reminder(list_name, item_text):
            updated_count += 1
        else:
            failed_items.append(item_text)

    # Add new items
    for item in items_to_add:
        if item.unit:
            item_text = f"{item.name} ({item.amount} {item.unit})"
        else:
            item_text = f"{item.name} ({item.amount})"
        if create_reminder(list_name, item_text):
            success_count += 1
        else:
            failed_items.append(item_text)

    ui.show_items_added(success_count, len(items_to_add), failed_items if failed_items else None, updated=updated_count)

    return {"reminders_added": True}
