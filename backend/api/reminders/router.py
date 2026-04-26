import asyncio
import logging

from fastapi import APIRouter

import reminders.client as reminders_client
from server.reorder import reorder_reminders_list
from .models import ReorderRemindersRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/reminder-lists")
async def get_reminder_lists():
    """Return all Apple Reminders list names."""
    lists = await asyncio.to_thread(reminders_client.get_all_lists)
    return {"lists": lists}


@router.post("/reorder-reminders")
async def reorder_reminders(request: ReorderRemindersRequest):
    """Reorder all items in a Reminders list by grocery store section order."""
    logger.info(f"POST /reorder-reminders - list_name={request.list_name!r}")
    return await reorder_reminders_list(request.list_name)
