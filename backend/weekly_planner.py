"""
CRUD operations for weekly meal planning.

Uses PostgreSQL when a connection pool is provided, falls back to a local JSON file
when running without a database (e.g. local dev with MemorySaver).
"""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

_FALLBACK_FILE = Path(__file__).parent.parent / "data" / "weekly_meals.json"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS weekly_meals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    day_of_week INTEGER NOT NULL,
    notes TEXT,
    url TEXT,
    week_start DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


def get_current_week_start() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


async def init_weekly_planner_table(pool) -> None:
    if pool is None:
        _FALLBACK_FILE.parent.mkdir(exist_ok=True)
        if not _FALLBACK_FILE.exists():
            _FALLBACK_FILE.write_text("[]")
        return
    async with pool.connection() as conn:
        await conn.execute(_CREATE_TABLE)


async def get_meals(pool) -> list[dict]:
    """Return all meals ordered by week_start DESC, day_of_week ASC."""
    if pool is None:
        items = _read_fallback()
        return sorted(items, key=lambda x: (-_date_key(x["week_start"]), x["day_of_week"]))
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id::text, name, day_of_week, notes, url, week_start::text"
            " FROM weekly_meals ORDER BY week_start DESC, day_of_week ASC"
        )
        rows = await cur.fetchall()
    return [{"id": r[0], "name": r[1], "day_of_week": r[2], "notes": r[3], "url": r[4], "week_start": r[5]} for r in rows]


async def create_meal(
    pool,
    name: str,
    day_of_week: int,
    week_start: str,
    notes: Optional[str] = None,
    url: Optional[str] = None,
) -> dict:
    if pool is None:
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
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO weekly_meals (name, day_of_week, notes, url, week_start)"
            " VALUES (%s, %s, %s, %s, %s)"
            " RETURNING id::text, name, day_of_week, notes, url, week_start::text",
            (name, day_of_week, notes, url, week_start),
        )
        row = await cur.fetchone()
    return {"id": row[0], "name": row[1], "day_of_week": row[2], "notes": row[3], "url": row[4], "week_start": row[5]}


async def update_meal(
    pool,
    id: str,
    name: str,
    day_of_week: int,
    notes: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[dict]:
    """Update a meal by id. week_start is not changed. Returns None if not found."""
    if pool is None:
        items = _read_fallback()
        for item in items:
            if item["id"] == id:
                item.update({"name": name, "day_of_week": day_of_week, "notes": notes, "url": url})
                _write_fallback(items)
                return item
        return None
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE weekly_meals SET name=%s, day_of_week=%s, notes=%s, url=%s"
            " WHERE id=%s::uuid"
            " RETURNING id::text, name, day_of_week, notes, url, week_start::text",
            (name, day_of_week, notes, url, id),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "day_of_week": row[2], "notes": row[3], "url": row[4], "week_start": row[5]}


async def delete_meal(pool, id: str) -> bool:
    if pool is None:
        items = _read_fallback()
        new_items = [i for i in items if i["id"] != id]
        if len(new_items) == len(items):
            return False
        _write_fallback(new_items)
        return True
    async with pool.connection() as conn:
        cur = await conn.execute("DELETE FROM weekly_meals WHERE id=%s::uuid", (id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# JSON fallback helpers
# ---------------------------------------------------------------------------

def _date_key(date_str: str) -> int:
    return int(date_str.replace("-", ""))


def _read_fallback() -> list[dict]:
    if not _FALLBACK_FILE.exists():
        return []
    return json.loads(_FALLBACK_FILE.read_text())


def _write_fallback(items: list[dict]) -> None:
    _FALLBACK_FILE.parent.mkdir(exist_ok=True)
    _FALLBACK_FILE.write_text(json.dumps(items, indent=2))
