"""
CRUD operations for working lists — internal shopping lists that can be exported
to Apple Reminders.

Uses SQLAlchemy AsyncSession when available, falls back to a local JSON file
when running without a database (e.g. local dev without DATABASE_URL).
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import WorkingList, WorkingListItem

_FALLBACK_FILE = Path(__file__).parent.parent / "data" / "working_lists.json"


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

async def get_lists(session: Optional[AsyncSession]) -> list[dict]:
    if session is None:
        data = _read_fallback()
        return [
            {"id": lst["id"], "name": lst["name"], "item_count": len(lst.get("items", []))}
            for lst in data
        ]
    result = await session.execute(select(WorkingList).order_by(WorkingList.created_at))
    lists = list(result.scalars())
    # Get item counts
    out = []
    for lst in lists:
        count_result = await session.execute(
            select(WorkingListItem).where(WorkingListItem.list_id == lst.id)
        )
        count = len(list(count_result.scalars()))
        out.append({"id": str(lst.id), "name": lst.name, "item_count": count})
    return out


async def create_list(session: Optional[AsyncSession], name: str) -> dict:
    if session is None:
        data = _read_fallback()
        lst = {"id": str(uuid.uuid4()), "name": name, "items": []}
        data.append(lst)
        _write_fallback(data)
        return {"id": lst["id"], "name": lst["name"], "item_count": 0}
    wl = WorkingList(name=name)
    session.add(wl)
    await session.commit()
    await session.refresh(wl)
    return {"id": str(wl.id), "name": wl.name, "item_count": 0}


async def delete_list(session: Optional[AsyncSession], list_id: str) -> bool:
    if session is None:
        data = _read_fallback()
        new_data = [l for l in data if l["id"] != list_id]
        if len(new_data) == len(data):
            return False
        _write_fallback(new_data)
        return True
    wl = await session.get(WorkingList, uuid.UUID(list_id))
    if wl is None:
        return False
    await session.delete(wl)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

async def get_list_items(session: Optional[AsyncSession], list_id: str) -> list[dict]:
    if session is None:
        data = _read_fallback()
        lst = _find_list(data, list_id)
        return list(lst.get("items", [])) if lst else []
    result = await session.execute(
        select(WorkingListItem)
        .where(WorkingListItem.list_id == uuid.UUID(list_id))
        .order_by(WorkingListItem.position, WorkingListItem.created_at)
    )
    return [_item_to_dict(item) for item in result.scalars()]


async def add_items(
    session: Optional[AsyncSession], list_id: str, items: list[dict]
) -> list[dict]:
    """Add multiple items to a working list. items: [{name, amount?, unit?}]"""
    if session is None:
        data = _read_fallback()
        lst = _find_list(data, list_id)
        if lst is None:
            return []
        existing = lst.setdefault("items", [])
        next_pos = max((i.get("position", 0) for i in existing), default=-1) + 1
        created = []
        for idx, item in enumerate(items):
            new_item = {
                "id": str(uuid.uuid4()),
                "name": item["name"],
                "amount": item.get("amount", ""),
                "unit": item.get("unit", ""),
                "position": next_pos + idx,
            }
            existing.append(new_item)
            created.append(new_item)
        _write_fallback(data)
        return created

    existing = await get_list_items(session, list_id)
    next_pos = max((i["position"] for i in existing), default=-1) + 1
    created = []
    for idx, item in enumerate(items):
        wli = WorkingListItem(
            list_id=uuid.UUID(list_id),
            name=item["name"],
            amount=item.get("amount", "") or "",
            unit=item.get("unit", "") or "",
            position=next_pos + idx,
        )
        session.add(wli)
        created.append(wli)
    await session.commit()
    for wli in created:
        await session.refresh(wli)
    return [_item_to_dict(wli) for wli in created]


async def update_item(
    session: Optional[AsyncSession],
    item_id: str,
    name: str,
    amount: str,
    unit: str,
) -> Optional[dict]:
    if session is None:
        data = _read_fallback()
        for lst in data:
            for item in lst.get("items", []):
                if item["id"] == item_id:
                    item["name"] = name
                    item["amount"] = amount
                    item["unit"] = unit
                    _write_fallback(data)
                    return dict(item)
        return None
    wli = await session.get(WorkingListItem, uuid.UUID(item_id))
    if wli is None:
        return None
    wli.name = name
    wli.amount = amount
    wli.unit = unit
    await session.commit()
    await session.refresh(wli)
    return _item_to_dict(wli)


async def delete_item(session: Optional[AsyncSession], item_id: str) -> bool:
    if session is None:
        data = _read_fallback()
        for lst in data:
            items = lst.get("items", [])
            new_items = [i for i in items if i["id"] != item_id]
            if len(new_items) < len(items):
                lst["items"] = new_items
                _write_fallback(data)
                return True
        return False
    wli = await session.get(WorkingListItem, uuid.UUID(item_id))
    if wli is None:
        return False
    await session.delete(wli)
    await session.commit()
    return True


async def clear_items(session: Optional[AsyncSession], list_id: str) -> int:
    if session is None:
        data = _read_fallback()
        lst = _find_list(data, list_id)
        if lst is None:
            return 0
        count = len(lst.get("items", []))
        lst["items"] = []
        _write_fallback(data)
        return count
    result = await session.execute(
        delete(WorkingListItem).where(WorkingListItem.list_id == uuid.UUID(list_id))
    )
    await session.commit()
    return result.rowcount


async def reorder_items(
    session: Optional[AsyncSession], list_id: str, item_ids: list[str]
) -> bool:
    """Update item positions based on the given ordered list of IDs."""
    if session is None:
        data = _read_fallback()
        lst = _find_list(data, list_id)
        if lst is None:
            return False
        id_to_pos = {iid: pos for pos, iid in enumerate(item_ids)}
        for item in lst.get("items", []):
            if item["id"] in id_to_pos:
                item["position"] = id_to_pos[item["id"]]
        lst["items"].sort(key=lambda i: i.get("position", 0))
        _write_fallback(data)
        return True
    for pos, iid in enumerate(item_ids):
        wli = await session.get(WorkingListItem, uuid.UUID(iid))
        if wli and str(wli.list_id) == list_id:
            wli.position = pos
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item_to_dict(item: WorkingListItem) -> dict:
    return {
        "id": str(item.id),
        "list_id": str(item.list_id),
        "name": item.name,
        "amount": item.amount or "",
        "unit": item.unit or "",
        "position": item.position,
    }


def _find_list(data: list[dict], list_id: str) -> Optional[dict]:
    return next((l for l in data if l["id"] == list_id), None)


def _read_fallback() -> list[dict]:
    if not _FALLBACK_FILE.exists():
        return []
    return json.loads(_FALLBACK_FILE.read_text())


def _write_fallback(data: list[dict]) -> None:
    _FALLBACK_FILE.parent.mkdir(exist_ok=True)
    _FALLBACK_FILE.write_text(json.dumps(data, indent=2))
