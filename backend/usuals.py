"""
CRUD operations for "usuals" — regular grocery items to restock.

Uses SQLAlchemy AsyncSession when available, falls back to a local JSON file
when running without a database (e.g. local dev without DATABASE_URL).
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Usual

_FALLBACK_FILE = Path(__file__).parent.parent / "data" / "usuals.json"


async def get_usuals(session: Optional[AsyncSession]) -> list[dict]:
    if session is None:
        return _read_fallback()
    result = await session.execute(
        select(Usual).order_by(Usual.category.nulls_last(), Usual.name)
    )
    return [_to_dict(u) for u in result.scalars()]


async def create_usual(session: Optional[AsyncSession], name: str, category: Optional[str] = None) -> dict:
    if session is None:
        item = {"id": str(uuid.uuid4()), "name": name, "category": category}
        items = _read_fallback()
        items.append(item)
        _write_fallback(items)
        return item
    usual = Usual(name=name, category=category)
    session.add(usual)
    await session.commit()
    await session.refresh(usual)
    return _to_dict(usual)


async def update_usual(session: Optional[AsyncSession], id: str, name: str, category: Optional[str] = None) -> Optional[dict]:
    if session is None:
        items = _read_fallback()
        for item in items:
            if item["id"] == id:
                item["name"] = name
                item["category"] = category
                _write_fallback(items)
                return item
        return None
    usual = await session.get(Usual, uuid.UUID(id))
    if usual is None:
        return None
    usual.name = name
    usual.category = category
    await session.commit()
    await session.refresh(usual)
    return _to_dict(usual)


async def delete_usual(session: Optional[AsyncSession], id: str) -> bool:
    if session is None:
        items = _read_fallback()
        new_items = [i for i in items if i["id"] != id]
        if len(new_items) == len(items):
            return False
        _write_fallback(new_items)
        return True
    usual = await session.get(Usual, uuid.UUID(id))
    if usual is None:
        return False
    await session.delete(usual)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_dict(u: Usual) -> dict:
    return {"id": str(u.id), "name": u.name, "category": u.category}


def _read_fallback() -> list[dict]:
    if not _FALLBACK_FILE.exists():
        return []
    return json.loads(_FALLBACK_FILE.read_text())


def _write_fallback(items: list[dict]) -> None:
    _FALLBACK_FILE.parent.mkdir(exist_ok=True)
    _FALLBACK_FILE.write_text(json.dumps(items, indent=2))
