"""
CRUD operations for "usuals" — regular grocery items to restock.

Uses PostgreSQL when a connection pool is provided, falls back to a local JSON file
when running without a database (e.g. local dev with MemorySaver).
"""

import json
import uuid
from pathlib import Path
from typing import Optional

_FALLBACK_FILE = Path(__file__).parent.parent / "data" / "usuals.json"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS usuals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


async def init_usuals_table(pool) -> None:
    """Create the usuals table if it doesn't exist."""
    if pool is None:
        _FALLBACK_FILE.parent.mkdir(exist_ok=True)
        if not _FALLBACK_FILE.exists():
            _FALLBACK_FILE.write_text("[]")
        return
    async with pool.connection() as conn:
        await conn.execute(_CREATE_TABLE)


async def get_usuals(pool) -> list[dict]:
    """Return all usuals ordered by category then name."""
    if pool is None:
        return _read_fallback()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id::text, name, category FROM usuals ORDER BY category NULLS LAST, name"
        )
        rows = await cur.fetchall()
    return [{"id": r[0], "name": r[1], "category": r[2]} for r in rows]


async def create_usual(pool, name: str, category: Optional[str] = None) -> dict:
    """Insert a new usual and return the created record."""
    if pool is None:
        item = {"id": str(uuid.uuid4()), "name": name, "category": category}
        items = _read_fallback()
        items.append(item)
        _write_fallback(items)
        return item
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO usuals (name, category) VALUES (%s, %s) RETURNING id::text, name, category",
            (name, category),
        )
        row = await cur.fetchone()
    return {"id": row[0], "name": row[1], "category": row[2]}


async def update_usual(pool, id: str, name: str, category: Optional[str] = None) -> Optional[dict]:
    """Update a usual by id. Returns None if not found."""
    if pool is None:
        items = _read_fallback()
        for item in items:
            if item["id"] == id:
                item["name"] = name
                item["category"] = category
                _write_fallback(items)
                return item
        return None
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE usuals SET name=%s, category=%s WHERE id=%s::uuid RETURNING id::text, name, category",
            (name, category, id),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "category": row[2]}


async def delete_usual(pool, id: str) -> bool:
    """Delete a usual by id. Returns True if a row was deleted."""
    if pool is None:
        items = _read_fallback()
        new_items = [i for i in items if i["id"] != id]
        if len(new_items) == len(items):
            return False
        _write_fallback(new_items)
        return True
    async with pool.connection() as conn:
        cur = await conn.execute("DELETE FROM usuals WHERE id=%s::uuid", (id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# JSON fallback helpers
# ---------------------------------------------------------------------------

def _read_fallback() -> list[dict]:
    if not _FALLBACK_FILE.exists():
        return []
    return json.loads(_FALLBACK_FILE.read_text())


def _write_fallback(items: list[dict]) -> None:
    _FALLBACK_FILE.parent.mkdir(exist_ok=True)
    _FALLBACK_FILE.write_text(json.dumps(items, indent=2))
