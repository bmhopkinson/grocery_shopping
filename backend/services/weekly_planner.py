"""
CRUD operations for weekly meal planning.

Uses SQLAlchemy AsyncSession when available, falls back to a local JSON file
when running without a database (e.g. local dev without DATABASE_URL).
"""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import WeeklyMeal

_FALLBACK_FILE = Path(__file__).parent.parent / "data" / "weekly_meals.json"


def get_current_week_start() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


async def get_meals(session: Optional[AsyncSession]) -> list[dict]:
    if session is None:
        items = _read_fallback()
        return sorted(items, key=lambda x: (-_date_key(x["week_start"]), x["day_of_week"]))
    result = await session.execute(
        select(WeeklyMeal).order_by(WeeklyMeal.week_start.desc(), WeeklyMeal.day_of_week)
    )
    return [_to_dict(m) for m in result.scalars()]


async def create_meal(
    session: Optional[AsyncSession],
    name: str,
    day_of_week: int,
    week_start: str,
    notes: Optional[str] = None,
    url: Optional[str] = None,
) -> dict:
    if session is None:
        item = {
            "id": str(uuid.uuid4()),
            "name": name,
            "day_of_week": day_of_week,
            "notes": notes,
            "url": url,
            "week_start": week_start,
        }
        items = _read_fallback()
        items.append(item)
        _write_fallback(items)
        return item
    meal = WeeklyMeal(
        name=name,
        day_of_week=day_of_week,
        week_start=date.fromisoformat(week_start),
        notes=notes,
        url=url,
    )
    session.add(meal)
    await session.commit()
    await session.refresh(meal)
    return _to_dict(meal)


async def update_meal(
    session: Optional[AsyncSession],
    id: str,
    name: str,
    day_of_week: int,
    notes: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[dict]:
    if session is None:
        items = _read_fallback()
        for item in items:
            if item["id"] == id:
                item.update({"name": name, "day_of_week": day_of_week, "notes": notes, "url": url})
                _write_fallback(items)
                return item
        return None
    meal = await session.get(WeeklyMeal, uuid.UUID(id))
    if meal is None:
        return None
    meal.name = name
    meal.day_of_week = day_of_week
    meal.notes = notes
    meal.url = url
    await session.commit()
    await session.refresh(meal)
    return _to_dict(meal)


async def delete_meal(session: Optional[AsyncSession], id: str) -> bool:
    if session is None:
        items = _read_fallback()
        new_items = [i for i in items if i["id"] != id]
        if len(new_items) == len(items):
            return False
        _write_fallback(new_items)
        return True
    meal = await session.get(WeeklyMeal, uuid.UUID(id))
    if meal is None:
        return False
    await session.delete(meal)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_dict(m: WeeklyMeal) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "day_of_week": m.day_of_week,
        "notes": m.notes,
        "url": m.url,
        "week_start": m.week_start.isoformat() if isinstance(m.week_start, date) else m.week_start,
    }


def _date_key(date_str: str) -> int:
    return int(date_str.replace("-", ""))


def _read_fallback() -> list[dict]:
    if not _FALLBACK_FILE.exists():
        return []
    return json.loads(_FALLBACK_FILE.read_text())


def _write_fallback(items: list[dict]) -> None:
    _FALLBACK_FILE.parent.mkdir(exist_ok=True)
    _FALLBACK_FILE.write_text(json.dumps(items, indent=2))
