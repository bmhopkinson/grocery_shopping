"""
Working list integration node.

Handles adding extracted ingredients to a working list (internal shopping list)
with smart collation of existing items.
"""

from langgraph.types import interrupt

from models import MealPlannerState, Ingredient
from collate import collate_ingredients
import ui


def format_item_text(item: Ingredient) -> str:
    if item.amount and item.unit:
        return f"{item.name} ({item.amount} {item.unit})"
    if item.amount:
        return f"{item.name} ({item.amount})"
    return item.name


async def add_to_working_list(state: MealPlannerState) -> dict:
    """
    Present final grocery list for approval and add to a working list.

    Interrupts to let the user pick or create a working list, then
    collates new ingredients with existing items in that list.

    Reads: grocery_list
    Writes: reminders_added
    """
    from database import get_session
    from working_list import get_lists, create_list, get_list_items, add_items, update_item

    ingredients = state.get("grocery_list", [])
    if not ingredients:
        ui.show_no_ingredients_for_reminders()
        return {"reminders_added": False}

    items_for_display = [
        {"name": item.name, "amount": item.amount, "unit": item.unit or ""}
        for item in ingredients
    ]

    async with get_session() as session:
        existing_lists = await get_lists(session)

    list_input = interrupt(value={
        "working_lists": [{"id": l["id"], "name": l["name"]} for l in existing_lists],
        "items": items_for_display,
        "instruction": "Select a shopping list or create a new one",
    })

    # Handle skip
    if isinstance(list_input, str) and list_input.strip().lower() in ("skip", "no", "cancel", ""):
        ui.show_skipping_reminders()
        return {"reminders_added": False}

    # Determine target list
    list_id = None
    list_name = None

    if isinstance(list_input, dict):
        action = list_input.get("action")
        if action == "select":
            list_id = list_input.get("list_id")
        elif action == "create":
            list_name = list_input.get("list_name", "").strip()
    elif isinstance(list_input, str):
        list_name = list_input.strip()

    async with get_session() as session:
        if list_id is None and list_name:
            new_list = await create_list(session, list_name)
            list_id = new_list["id"]

        if list_id is None:
            return {"reminders_added": False}

        # Load existing items and build text lookup for collation
        existing_items = await get_list_items(session, list_id)
        existing_texts = []
        item_id_by_text: dict[str, str] = {}
        for item in existing_items:
            text = format_item_text(Ingredient(
                name=item["name"],
                amount=item["amount"] or "",
                unit=item["unit"] or "",
            ))
            existing_texts.append(text)
            item_id_by_text[text] = item["id"]

        items_to_add, items_to_update = collate_ingredients(existing_texts, ingredients)

        # Apply combined updates
        for old_text, combined in items_to_update:
            item_id = item_id_by_text.get(old_text)
            if item_id:
                await update_item(session, item_id, combined.name, combined.amount, combined.unit or "")

        # Add new items
        if items_to_add:
            await add_items(session, list_id, [
                {"name": i.name, "amount": i.amount, "unit": i.unit or ""}
                for i in items_to_add
            ])

    total = len(items_to_add) + len(items_to_update)
    ui.show_items_added(
        len(items_to_add),
        total,
        None,
        updated=len(items_to_update),
    )

    return {"reminders_added": True}


# Keep legacy function name for any CLI usage
def add_to_reminders(state: MealPlannerState) -> dict:
    import asyncio
    return asyncio.run(add_to_working_list(state))
