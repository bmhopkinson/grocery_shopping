"""
Apple Reminders integration node.

Handles adding ingredients to Apple Reminders lists with smart collation.
"""

from langgraph.types import interrupt

from models import MealPlannerState, Ingredient
from reminders import (
    create_reminder,
    list_exists,
    create_list,
    get_all_lists,
    get_reminders,
    delete_reminders_batch,
)
from collate import collate_ingredients
import ui


def format_reminder_item(item: Ingredient) -> str:
    """Format an ingredient as a reminder item text."""
    if item.unit:
        return f"{item.name} ({item.amount} {item.unit})"
    return f"{item.name} ({item.amount})"


def add_to_reminders(state: MealPlannerState) -> dict:
    """
    Present final grocery list for approval and add to Apple Reminders.

    Handles list selection (existing or new), smart collation with
    existing items, and batch operations for efficiency.

    Reads: grocery_list
    Writes: reminders_added
    """
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

    list_input_str = str(list_input).strip()

    if list_input_str.lower() in ("skip", "no", "cancel", ""):
        ui.show_skipping_reminders()
        return {"reminders_added": False}

    # Determine list name
    if list_input_str.isdigit():
        idx = int(list_input_str) - 1
        if 0 <= idx < len(existing_lists):
            list_name = existing_lists[idx]
        else:
            list_name = list_input_str  # Use as literal name if out of range
    else:
        list_name = list_input_str

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
        item_text = format_reminder_item(combined)
        if create_reminder(list_name, item_text):
            updated_count += 1
        else:
            failed_items.append(item_text)

    # Add new items
    for item in items_to_add:
        item_text = format_reminder_item(item)
        if create_reminder(list_name, item_text):
            success_count += 1
        else:
            failed_items.append(item_text)

    ui.show_items_added(
        success_count,
        len(items_to_add),
        failed_items if failed_items else None,
        updated=updated_count
    )

    return {"reminders_added": True}
