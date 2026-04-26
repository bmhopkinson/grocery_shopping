import logging

from fastapi import APIRouter, HTTPException

from database import get_session
from services.weekly_planner import get_meals, create_meal, update_meal, delete_meal
from .models import MealCreateRequest, MealUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/weekly-meals")
async def list_weekly_meals():
    async with get_session() as session:
        return await get_meals(session)


@router.post("/weekly-meals")
async def create_weekly_meal(request: MealCreateRequest):
    async with get_session() as session:
        return await create_meal(session, request.name, request.day_of_week, request.week_start, request.notes, request.url)


@router.put("/weekly-meals/{id}")
async def update_weekly_meal(id: str, request: MealUpdateRequest):
    async with get_session() as session:
        item = await update_meal(session, id, request.name, request.day_of_week, request.notes, request.url)
    if item is None:
        raise HTTPException(status_code=404, detail="Meal not found")
    return item


@router.delete("/weekly-meals/{id}")
async def delete_weekly_meal(id: str):
    async with get_session() as session:
        deleted = await delete_meal(session, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"deleted": True}
