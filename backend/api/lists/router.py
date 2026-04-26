import asyncio
import logging

from fastapi import APIRouter, HTTPException

import reminders.client as reminders_client
from reminders.collate import collate_ingredients
from database import get_session
from agent.models import Ingredient
import services.working_list as wl_crud
from server.reorder import STORE_SECTION_ORDER, ReorderedList
from agent.nodes.base import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from .models import (
    WorkingListCreateRequest,
    WorkingListItemCreateRequest,
    WorkingListItemUpdateRequest,
    WorkingListReorderRequest,
    WorkingListDumpRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/working-lists")
async def list_working_lists():
    async with get_session() as session:
        return await wl_crud.get_lists(session)


@router.post("/working-lists")
async def create_working_list(request: WorkingListCreateRequest):
    async with get_session() as session:
        return await wl_crud.create_list(session, request.name)


@router.delete("/working-lists/{list_id}")
async def delete_working_list(list_id: str):
    async with get_session() as session:
        deleted = await wl_crud.delete_list(session, list_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Working list not found")
    return {"deleted": True}


@router.get("/working-lists/{list_id}/items")
async def get_working_list_items(list_id: str):
    async with get_session() as session:
        return await wl_crud.get_list_items(session, list_id)


@router.post("/working-lists/{list_id}/items")
async def add_working_list_item(list_id: str, request: WorkingListItemCreateRequest):
    async with get_session() as session:
        created = await wl_crud.add_items(
            session, list_id,
            [{"name": request.name, "amount": request.amount, "unit": request.unit}]
        )
    return created[0] if created else {}


@router.put("/working-lists/{list_id}/items/{item_id}")
async def update_working_list_item(list_id: str, item_id: str, request: WorkingListItemUpdateRequest):
    async with get_session() as session:
        item = await wl_crud.update_item(session, item_id, request.name, request.amount, request.unit)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/working-lists/{list_id}/items/{item_id}")
async def delete_working_list_item(list_id: str, item_id: str):
    async with get_session() as session:
        deleted = await wl_crud.delete_item(session, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True}


@router.delete("/working-lists/{list_id}/items")
async def clear_working_list(list_id: str):
    async with get_session() as session:
        count = await wl_crud.clear_items(session, list_id)
    return {"cleared": count}


@router.post("/working-lists/{list_id}/reorder")
async def reorder_working_list(list_id: str, request: WorkingListReorderRequest):
    async with get_session() as session:
        items = await wl_crud.get_list_items(session, list_id)

    if not items:
        return {"reordered": [], "count": 0}

    item_texts = [
        f"{i['name']} ({i['amount']} {i['unit']}".rstrip() + ")" if i.get("amount") else i["name"]
        for i in items
    ]
    sections_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(STORE_SECTION_ORDER))
    items_text = "\n".join(f"- {t}" for t in item_texts)
    system = (
        "You are a grocery store layout expert. Sort grocery lists by physical store section "
        "so a shopper can walk front-to-back without backtracking.\n\n"
        "Rules:\n"
        "- Return every item EXACTLY as given.\n"
        "- Each item appears exactly once.\n"
        "- Group by store section and sort groups in the section order provided."
    )
    prompt = (
        f"Store sections (in order):\n{sections_text}\n\n"
        f"Items to sort ({len(item_texts)}):\n{items_text}\n\n"
        f"Return all {len(item_texts)} items sorted by section."
    )

    llm = get_llm()
    response = await llm.with_structured_output(ReorderedList).ainvoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)]
    )
    reordered_texts = response.items

    text_to_id = {t: items[i]["id"] for i, t in enumerate(item_texts)}
    reordered_ids = [text_to_id[t] for t in reordered_texts if t in text_to_id]
    matched_ids = set(reordered_ids)
    reordered_ids += [i["id"] for i in items if i["id"] not in matched_ids]

    async with get_session() as session:
        await wl_crud.reorder_items(session, list_id, reordered_ids)
        final_items = await wl_crud.get_list_items(session, list_id)

    logger.info(f"reorder_working_list: reordered {len(final_items)} items in list {list_id!r}")
    return {"reordered": final_items, "count": len(final_items)}


@router.post("/working-lists/{list_id}/dump-to-reminders")
async def dump_working_list_to_reminders(list_id: str, request: WorkingListDumpRequest):
    """Export all items in a working list to an Apple Reminders list with smart collation."""
    async with get_session() as session:
        items = await wl_crud.get_list_items(session, list_id)

    if not items:
        raise HTTPException(status_code=400, detail="Working list is empty")

    list_name = request.list_name
    list_exists = await asyncio.to_thread(reminders_client.list_exists, list_name)
    if not list_exists:
        await asyncio.to_thread(reminders_client.create_list, list_name)

    existing_texts = await asyncio.to_thread(reminders_client.get_reminders, list_name)
    ingredients = [
        Ingredient(name=i["name"], amount=i["amount"] or "", unit=i["unit"] or "")
        for i in items
    ]
    items_to_add, items_to_update = collate_ingredients(existing_texts, ingredients)

    if items_to_update:
        old_texts = [old_text for old_text, _ in items_to_update]
        await asyncio.to_thread(reminders_client.delete_reminders_batch, list_name, old_texts)

    def _fmt(item: Ingredient) -> str:
        if item.amount and item.unit:
            return f"{item.name} ({item.amount} {item.unit})"
        if item.amount:
            return f"{item.name} ({item.amount})"
        return item.name

    added, failed = [], []
    for _, combined in items_to_update:
        text = _fmt(combined)
        ok = await asyncio.to_thread(reminders_client.create_reminder, list_name, text)
        (added if ok else failed).append(text)
    for item in items_to_add:
        text = _fmt(item)
        ok = await asyncio.to_thread(reminders_client.create_reminder, list_name, text)
        (added if ok else failed).append(text)

    logger.info(f"dump_working_list_to_reminders: added={len(added)} failed={len(failed)} list={list_name!r}")
    return {"added": len(added), "failed": failed, "list_name": list_name}
