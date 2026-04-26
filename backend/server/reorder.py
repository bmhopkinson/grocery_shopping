"""
Grocery list reordering by store section layout.
"""

import asyncio
import logging

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

import reminders.client as reminders_client
from agent.nodes.base import get_llm


logger = logging.getLogger(__name__)


STORE_SECTION_ORDER = [
    "deli",
    "fresh bread",
    "speciality cheese",
    "produce",
    "meat",
    "pickles, mayo, salad dressing",
    "international dry goods",
    "pasta, tomato sauce, italian dry goods",
    "soup, broth, bullion",
    "cereal and breakfast snacks",
    "peanut butter and jelly",
    "coffee",
    "baking goods, spices",
    "cooking oils and vinegar",
    "cookies, chocolate, candy",
    "snacks - chips, pretzels, popcorn",
    "packaged bread and rolls",
    "dairy and eggs",
    "frozen",
    "beer and wine",
    "paper items",
    "pharmacy",
]


class ReorderedList(BaseModel):
    items: list[str]


async def reorder_reminders_list(list_name: str) -> dict:
    """
    Fetch a Reminders list, sort items by store section layout using an LLM,
    then delete and re-create them in the new order.

    Returns dict with list_name, reordered_items, and count.
    Raises HTTPException on LLM output mismatch.
    """
    items = await asyncio.to_thread(reminders_client.get_reminders, list_name)
    if not items:
        return {"list_name": list_name, "reordered_items": [], "count": 0}

    sections_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(STORE_SECTION_ORDER))
    items_text = "\n".join(f"- {item}" for item in items)
    system = (
        "You are a grocery store layout expert. Your job is to sort grocery lists by physical "
        "store section so a shopper can walk front-to-back without backtracking.\n\n"
        "Rules:\n"
        "- Return every item EXACTLY as given — do not alter text, spelling, or quantity info in parentheses.\n"
        "- Each item appears exactly once.\n"
        "- Group items by their most likely store section and sort groups in the section order provided.\n"
        "- Within each section, keep items in any order.\n"
        "- Items that don't clearly fit any section go at the very end.\n"
        "- Use common sense: eggs → dairy, butter → dairy, chicken → meat, apples → produce, "
        "olive oil → cooking oils and vinegar, flour/sugar → baking goods, etc."
    )
    prompt = (
        f"Store sections (in order, front to back):\n{sections_text}\n\n"
        f"Grocery list to sort ({len(items)} items):\n{items_text}\n\n"
        f"Return all {len(items)} items sorted by section order. "
        f"Copy each item verbatim — including any quantity in parentheses."
    )

    llm = get_llm()
    response = await llm.with_structured_output(ReorderedList).ainvoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)]
    )
    reordered = response.items

    if abs(len(reordered) - len(items)) > 2:
        logger.warning(
            f"reorder_reminders_list: item count mismatch original={len(items)} reordered={len(reordered)}"
        )
        raise HTTPException(status_code=500, detail="LLM returned unexpected item count")

    await asyncio.to_thread(reminders_client.delete_reminders_batch, list_name, items)
    for item in reordered:
        await asyncio.to_thread(reminders_client.create_reminder, list_name, item)

    logger.info(f"reorder_reminders_list: reordered {len(reordered)} items in {list_name!r}")
    return {"list_name": list_name, "reordered_items": reordered, "count": len(reordered)}
