import asyncio
import logging

from fastapi import APIRouter, HTTPException

import reminders.client as reminders_client
from database import get_session
from services.usuals import get_usuals, create_usual, update_usual, delete_usual
import services.working_list as wl_crud
from .models import (
    UsualCreateRequest,
    UsualUpdateRequest,
    AddUsualsToRemindersRequest,
    AddUsualsToWorkingListRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/usuals")
async def list_usuals():
    async with get_session() as session:
        return await get_usuals(session)


@router.post("/usuals/add-to-reminders")
async def add_usuals_to_reminders(request: AddUsualsToRemindersRequest):
    async with get_session() as session:
        all_usuals = await get_usuals(session)
    id_set = set(request.usual_ids)
    selected = [u for u in all_usuals if u["id"] in id_set]

    if not selected:
        raise HTTPException(status_code=400, detail="No matching usuals found")

    list_exists = await asyncio.to_thread(reminders_client.list_exists, request.list_name)
    if not list_exists:
        await asyncio.to_thread(reminders_client.create_list, request.list_name)

    added, failed = [], []
    for item in selected:
        ok = await asyncio.to_thread(reminders_client.create_reminder, request.list_name, item["name"])
        (added if ok else failed).append(item["name"])

    logger.info(f"add_usuals_to_reminders: added={added}, failed={failed}, list={request.list_name!r}")
    return {"added": added, "failed": failed, "list_name": request.list_name}


@router.post("/usuals/add-to-working-list")
async def add_usuals_to_working_list(request: AddUsualsToWorkingListRequest):
    async with get_session() as session:
        all_usuals = await get_usuals(session)
    id_set = set(request.usual_ids)
    selected = [u for u in all_usuals if u["id"] in id_set]
    if not selected:
        raise HTTPException(status_code=400, detail="No matching usuals found")

    async with get_session() as session:
        created = await wl_crud.add_items(
            session,
            request.working_list_id,
            [{"name": u["name"]} for u in selected],
        )
    logger.info(f"add_usuals_to_working_list: added {len(created)} items to list {request.working_list_id!r}")
    return {"added": [i["name"] for i in created], "working_list_id": request.working_list_id}


@router.post("/usuals")
async def create_usual_endpoint(request: UsualCreateRequest):
    async with get_session() as session:
        return await create_usual(session, request.name, request.category)


@router.put("/usuals/{id}")
async def update_usual_endpoint(id: str, request: UsualUpdateRequest):
    async with get_session() as session:
        item = await update_usual(session, id, request.name, request.category)
    if item is None:
        raise HTTPException(status_code=404, detail="Usual not found")
    return item


@router.delete("/usuals/{id}")
async def delete_usual_endpoint(id: str):
    async with get_session() as session:
        deleted = await delete_usual(session, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usual not found")
    return {"deleted": True}
