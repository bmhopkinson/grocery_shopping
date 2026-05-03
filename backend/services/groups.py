import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RecipeGroup, Recipe


def _group_to_dict(g: RecipeGroup) -> dict:
    return {"id": str(g.id), "name": g.name}


async def get_groups(session: AsyncSession) -> list[dict]:
    rows = await session.execute(
        select(RecipeGroup, func.count(Recipe.id).label("recipe_count"))
        .outerjoin(Recipe, Recipe.group_id == RecipeGroup.id)
        .group_by(RecipeGroup.id)
        .order_by(RecipeGroup.name)
    )
    groups = [
        {"id": str(g.id), "name": g.name, "recipe_count": count}
        for g, count in rows
    ]

    uncategorized_count = (
        await session.execute(
            select(func.count(Recipe.id)).where(Recipe.group_id.is_(None))
        )
    ).scalar()
    if uncategorized_count:
        groups.append({"id": None, "name": "Uncategorized", "recipe_count": uncategorized_count})

    return groups


async def get_group_by_name(session: AsyncSession, name: str) -> Optional[dict]:
    result = await session.execute(select(RecipeGroup).where(RecipeGroup.name == name))
    g = result.scalar_one_or_none()
    return _group_to_dict(g) if g else None


async def create_group(session: AsyncSession, name: str) -> dict:
    group = RecipeGroup(name=name)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return _group_to_dict(group)


async def delete_group(session: AsyncSession, group_id: str) -> bool:
    result = await session.execute(select(RecipeGroup).where(RecipeGroup.id == uuid.UUID(group_id)))
    group = result.scalar_one_or_none()
    if not group:
        return False
    await session.delete(group)
    await session.commit()
    return True
