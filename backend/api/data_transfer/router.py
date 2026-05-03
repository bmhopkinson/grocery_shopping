import base64
import json
import uuid
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete

from database import get_session
from database.models import (
    Usual,
    WeeklyMeal,
    WorkingList,
    WorkingListItem,
    RecipeGroup,
    Recipe,
    RecipeIngredient,
)

router = APIRouter()

EXPORT_VERSION = 1


@router.get("/export")
async def export_data():
    async with get_session() as session:
        usuals = (await session.execute(select(Usual).order_by(Usual.created_at))).scalars().all()
        weekly_meals = (await session.execute(select(WeeklyMeal).order_by(WeeklyMeal.created_at))).scalars().all()
        working_lists = (await session.execute(select(WorkingList).order_by(WorkingList.created_at))).scalars().all()
        wl_items = (
            await session.execute(
                select(WorkingListItem).order_by(WorkingListItem.list_id, WorkingListItem.position)
            )
        ).scalars().all()
        recipe_groups = (await session.execute(select(RecipeGroup).order_by(RecipeGroup.created_at))).scalars().all()
        recipes = (await session.execute(select(Recipe).order_by(Recipe.created_at))).scalars().all()
        recipe_ingredients = (
            await session.execute(
                select(RecipeIngredient).order_by(RecipeIngredient.recipe_id, RecipeIngredient.position)
            )
        ).scalars().all()

    items_by_list: dict[str, list] = {}
    for item in wl_items:
        items_by_list.setdefault(str(item.list_id), []).append({
            "id": str(item.id),
            "name": item.name,
            "amount": item.amount,
            "unit": item.unit,
            "position": item.position,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    ingredients_by_recipe: dict[str, list] = {}
    for ing in recipe_ingredients:
        ingredients_by_recipe.setdefault(str(ing.recipe_id), []).append({
            "id": str(ing.id),
            "name": ing.name,
            "amount": ing.amount,
            "unit": ing.unit,
            "position": ing.position,
            "created_at": ing.created_at.isoformat() if ing.created_at else None,
        })

    data = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "usuals": [
            {
                "id": str(u.id),
                "name": u.name,
                "category": u.category,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in usuals
        ],
        "weekly_meals": [
            {
                "id": str(m.id),
                "name": m.name,
                "day_of_week": m.day_of_week,
                "notes": m.notes,
                "url": m.url,
                "week_start": m.week_start.isoformat() if m.week_start else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in weekly_meals
        ],
        "working_lists": [
            {
                "id": str(wl.id),
                "name": wl.name,
                "created_at": wl.created_at.isoformat() if wl.created_at else None,
                "items": items_by_list.get(str(wl.id), []),
            }
            for wl in working_lists
        ],
        "recipe_groups": [
            {
                "id": str(g.id),
                "name": g.name,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in recipe_groups
        ],
        "recipes": [
            {
                "id": str(r.id),
                "name": r.name,
                "url": r.url,
                "notes": r.notes,
                "instructions": r.instructions,
                "image_data": base64.b64encode(r.image_data).decode() if r.image_data else None,
                "image_content_type": r.image_content_type,
                "group_id": str(r.group_id) if r.group_id else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "ingredients": ingredients_by_recipe.get(str(r.id), []),
            }
            for r in recipes
        ],
    }

    json_bytes = json.dumps(data, indent=2).encode()
    filename = f"grocery_shopping_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import")
async def import_data(file: UploadFile = File(...)):
    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if data.get("version") != EXPORT_VERSION:
        raise HTTPException(status_code=400, detail=f"Unsupported export version: {data.get('version')}")

    async with get_session() as session:
        # Delete in FK-safe order
        await session.execute(delete(RecipeIngredient))
        await session.execute(delete(Recipe))
        await session.execute(delete(RecipeGroup))
        await session.execute(delete(WorkingListItem))
        await session.execute(delete(WorkingList))
        await session.execute(delete(WeeklyMeal))
        await session.execute(delete(Usual))

        for u in data.get("usuals", []):
            session.add(Usual(id=uuid.UUID(u["id"]), name=u["name"], category=u.get("category")))

        for m in data.get("weekly_meals", []):
            session.add(WeeklyMeal(
                id=uuid.UUID(m["id"]),
                name=m["name"],
                day_of_week=m["day_of_week"],
                notes=m.get("notes"),
                url=m.get("url"),
                week_start=date.fromisoformat(m["week_start"]),
            ))

        for wl in data.get("working_lists", []):
            session.add(WorkingList(id=uuid.UUID(wl["id"]), name=wl["name"]))
            for item in wl.get("items", []):
                session.add(WorkingListItem(
                    id=uuid.UUID(item["id"]),
                    list_id=uuid.UUID(wl["id"]),
                    name=item["name"],
                    amount=item.get("amount"),
                    unit=item.get("unit"),
                    position=item.get("position", 0),
                ))

        for g in data.get("recipe_groups", []):
            session.add(RecipeGroup(id=uuid.UUID(g["id"]), name=g["name"]))

        for r in data.get("recipes", []):
            image_data = base64.b64decode(r["image_data"]) if r.get("image_data") else None
            session.add(Recipe(
                id=uuid.UUID(r["id"]),
                name=r["name"],
                url=r.get("url"),
                notes=r.get("notes"),
                instructions=r.get("instructions"),
                image_data=image_data,
                image_content_type=r.get("image_content_type"),
                group_id=uuid.UUID(r["group_id"]) if r.get("group_id") else None,
            ))
            for ing in r.get("ingredients", []):
                session.add(RecipeIngredient(
                    id=uuid.UUID(ing["id"]),
                    recipe_id=uuid.UUID(r["id"]),
                    name=ing["name"],
                    amount=ing.get("amount"),
                    unit=ing.get("unit"),
                    position=ing.get("position", 0),
                ))

        await session.commit()

    return {
        "imported": {
            "usuals": len(data.get("usuals", [])),
            "weekly_meals": len(data.get("weekly_meals", [])),
            "working_lists": len(data.get("working_lists", [])),
            "recipe_groups": len(data.get("recipe_groups", [])),
            "recipes": len(data.get("recipes", [])),
        }
    }
