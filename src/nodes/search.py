"""
Search-related graph nodes.

Handles recipe discovery, parsing, validation, and refinement.
"""

from typing import List

from langchain_core.messages import AIMessage

from models import (
    MealPlannerState,
    MealOption,
    ParsedRecipes,
    ValidationResult,
    DishNames,
)
from prompts import (
    get_parse_recipes_prompt,
    get_validate_recipes_prompt,
    get_dish_names_prompt,
    get_refine_search_prompt,
    get_refine_search_query,
)
from nodes.base import get_llm, get_search_tool, invoke_structured
import ui


def search_meals(state: MealPlannerState) -> dict:
    """
    Search the web for meal ideas and recipe links based on cuisine type.

    Reads: cuisine_type
    Writes: search_results
    """
    cuisine = state["cuisine_type"]
    ui.show_searching(cuisine)

    search_tool = get_search_tool()
    query = f"{cuisine} dinner recipe with ingredients"
    results = search_tool.invoke(query)

    ui.show_search_complete()
    return {"search_results": results}


def parse_meals(state: MealPlannerState) -> dict:
    """
    Use LLM to parse search results into structured meal options with recipe URLs.

    Reads: search_results, cuisine_type
    Writes: meal_options, messages
    """
    search_results = state["search_results"]
    cuisine = state["cuisine_type"]

    ui.show_parsing()

    parse_prompt = get_parse_recipes_prompt(cuisine, search_results)
    result: ParsedRecipes = invoke_structured(ParsedRecipes, parse_prompt)

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
    """
    Validate that recipe URLs point to single recipes, not collections.

    If fewer than 3 valid recipes are found and refinement hasn't been
    exhausted, triggers the refinement flow.

    Reads: meal_options, cuisine_type, refinement_count
    Writes: meal_options, refinement_count (conditional), refine_dishes (conditional)
    """
    meal_options = state["meal_options"]
    cuisine = state["cuisine_type"]
    refinement_count = state.get("refinement_count", 0)

    ui.show_validating(refinement_count + 1)

    recipes_text = "\n".join([
        f"- {opt.name}: {opt.description} (URL: {opt.recipe_url})"
        for opt in meal_options
    ])

    validate_prompt = get_validate_recipes_prompt(recipes_text, cuisine)
    result: ValidationResult = invoke_structured(ValidationResult, validate_prompt)

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
    """
    Search for specific dish names to get direct recipe links.

    Used when initial search didn't yield enough valid single-recipe URLs.

    Reads: cuisine_type, preferred_sources, refine_dishes, meal_options
    Writes: meal_options, search_results, refine_dishes
    """
    cuisine = state["cuisine_type"]
    sources = state.get("preferred_sources", [])
    dish_names = state.get("refine_dishes", [])
    existing_valid = state.get("meal_options", [])

    search_tool = get_search_tool()

    # Generate dish names if not provided
    if not dish_names:
        dish_prompt = get_dish_names_prompt(cuisine)
        result: DishNames = invoke_structured(DishNames, dish_prompt)
        dish_names = result.dishes[:5]

    ui.show_searching_dishes(dish_names)

    # Search for each specific dish
    all_results = []
    for dish in dish_names[:5]:
        query = get_refine_search_query(dish, sources)
        results = search_tool.invoke(query)
        all_results.append(f"--- {dish} ---\n{results}")

    combined_results = "\n\n".join(all_results)

    # Parse combined results
    parse_prompt = get_refine_search_prompt(combined_results, sources)
    result: ParsedRecipes = invoke_structured(ParsedRecipes, parse_prompt)

    # Combine with existing valid recipes
    all_recipes = existing_valid + [
        MealOption(
            id=0,
            name=recipe.name,
            description=recipe.description,
            recipe_url=recipe.url
        )
        for recipe in result.recipes
    ]

    # Deduplicate by URL
    seen_urls = set()
    unique_recipes: List[MealOption] = []
    for r in all_recipes:
        if r.recipe_url and r.recipe_url not in seen_urls:
            seen_urls.add(r.recipe_url)
            unique_recipes.append(r)

    # Re-index
    unique_recipes = [
        MealOption(id=i, name=r.name, description=r.description, recipe_url=r.recipe_url)
        for i, r in enumerate(unique_recipes[:5], 1)
    ]

    ui.show_refinement_complete(len(unique_recipes))
    return {
        "meal_options": unique_recipes[:5],
        "search_results": combined_results,
        "refine_dishes": None  # Clear to exit refinement loop
    }
