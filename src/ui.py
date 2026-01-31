"""
UI abstraction layer for the Meal Planner agent.

This module provides display functions that can be configured for CLI or GUI modes.
Set CLI_MODE=false in .env to disable terminal output (for GUI integration).
"""

import os
import sys
from pathlib import Path
from typing import List

# Add src directory to Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from models import MealOption, Ingredient

# Configuration from environment
CLI_MODE = os.getenv("CLI_MODE", "true").lower() == "true"


def _print(text: str) -> None:
    """Print only if CLI mode is enabled."""
    if CLI_MODE:
        print(text)


# --- Status Messages ---

def show_searching(cuisine: str) -> None:
    _print(f"🔍 Searching for {cuisine} recipes...")


def show_search_complete() -> None:
    _print("📋 Found recipe search results")


def show_parsing() -> None:
    _print("🤖 Parsing recipes from search results...")


def show_parsed_count(count: int) -> None:
    _print(f"✅ Parsed {count} recipes with URLs")


def show_validating(attempt: int) -> None:
    _print(f"🔍 Validating recipe URLs (attempt {attempt})...")


def show_valid_count(count: int) -> None:
    _print(f"✅ Found {count} valid single-recipe URLs")


def show_refining() -> None:
    _print("🔄 Not enough valid recipes. Searching for specific dishes...")


def show_searching_dishes(dishes: List[str]) -> None:
    _print(f"🔍 Searching for specific recipes: {', '.join(dishes[:3])}...")


def show_refinement_complete(count: int) -> None:
    _print(f"✅ Found {count} recipes after refinement")


def show_fetching_recipe(url: str) -> None:
    _print(f"🔗 Fetching recipe from: {url}")


def show_found_structured_data() -> None:
    _print("📋 Found structured recipe data")


def show_extracting_text() -> None:
    _print("📄 Extracting text from page...")


def show_extracting_ingredients() -> None:
    _print("🤖 Extracting ingredients...")


def show_extracted_count(count: int) -> None:
    _print(f"✅ Extracted {count} ingredients")


def show_user_input(value: str) -> None:
    _print(f"✅ User input: {value}")


def show_user_selection(value: str) -> None:
    _print(f"✅ User selected: {value}")


def show_removed_count(count: int) -> None:
    _print(f"✅ Removed {count} items")


def show_creating_list(list_name: str) -> None:
    _print(f"📝 Creating '{list_name}' list...")


def show_adding_items(count: int, list_name: str, updated: int = 0) -> None:
    if updated > 0:
        _print(f"📥 Adding {count} items to '{list_name}' ({updated} merged with existing)...")
    else:
        _print(f"📥 Adding {count} items to '{list_name}'...")


def show_items_added(success: int, total: int, failed: List[str] | None = None, updated: int = 0) -> None:
    if failed:
        _print(f"⚠️  Added {success}/{total} items. Failed: {', '.join(failed)}")
    elif updated > 0:
        _print(f"✅ Added {success} new items, merged {updated} with existing items")
    else:
        _print(f"✅ Successfully added all {success} items")


def show_skipping_reminders() -> None:
    _print("⏭️  Skipping Reminders - items not added")


# --- Error Messages ---

def show_error(message: str) -> None:
    _print(f"❌ {message}")


def show_no_recipe_url() -> None:
    _print("❌ No recipe URL available")


def show_fetch_error(error: str) -> None:
    _print(f"❌ Failed to fetch recipe: {error}")


def show_no_ingredients() -> None:
    _print("❌ No ingredients to review")


def show_no_ingredients_for_reminders() -> None:
    _print("❌ No ingredients to add to Reminders")


def show_list_creation_failed(list_name: str) -> None:
    _print(f"❌ Failed to create list '{list_name}'")


# --- Interactive Prompts ---

def format_recipe_options(cuisine: str, meal_options: List[MealOption]) -> str:
    """Format recipe options for display. Returns the formatted text."""
    text = f"\n🍽️  Here are some {cuisine} recipes:\n\n"
    for option in meal_options:
        text += f"{option.id}. **{option.name}**: {option.description}\n"
        if option.recipe_url:
            text += f"   🔗 {option.recipe_url}\n"
    text += "\n📝 Please enter the number of the recipe you'd like to make (1-5):"
    return text


def show_recipe_options(cuisine: str, meal_options: List[MealOption]) -> str:
    """Display recipe options and return the formatted text."""
    text = format_recipe_options(cuisine, meal_options)
    _print(text)
    return text


def format_ingredients_review(ingredients: List[Ingredient]) -> str:
    """Format ingredients for review. Returns the formatted text."""
    text = "\n🛒 Extracted Ingredients:\n"
    text += "-" * 40 + "\n"
    for i, item in enumerate(ingredients, 1):
        if item.unit:
            text += f"{i}. {item.amount} {item.unit} {item.name}\n"
        else:
            text += f"{i}. {item.amount} {item.name}\n"
    text += "-" * 40
    text += "\nEnter 'ok' to approve, or 'remove 1, 3, 5' to remove items:"
    return text


def show_ingredients_review(ingredients: List[Ingredient]) -> str:
    """Display ingredients for review and return the formatted text."""
    text = format_ingredients_review(ingredients)
    _print(text)
    return text


def format_reminders_prompt(
    items_display: str,
    item_count: int,
    existing_lists: List[str]
) -> str:
    """Format the reminders list selection prompt. Returns the formatted text."""
    text = "\n📋 Grocery List Items:\n"
    text += "=" * 45 + "\n"
    text += items_display
    text += "=" * 45
    text += "\n\n📝 Which Reminders list should these be added to?\n"

    if existing_lists:
        text += "\nExisting lists:\n"
        for i, lst in enumerate(existing_lists, 1):
            text += f"  {i}. {lst}\n"
        text += "\nEnter a number to select, a new list name, or 'skip' to cancel:"
    else:
        text += "\nEnter a list name (will be created if needed), or 'skip' to cancel:"

    return text


def show_reminders_prompt(
    items_display: str,
    item_count: int,
    existing_lists: List[str]
) -> str:
    """Display reminders prompt and return the formatted text."""
    text = format_reminders_prompt(items_display, item_count, existing_lists)
    _print(text)
    return text
