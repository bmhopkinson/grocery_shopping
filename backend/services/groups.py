import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RecipeGroup


def _group_to_dict(g: RecipeGroup) -> dict:
    return {"id": str(g.id), "name": g.name}


async def get_groups(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(RecipeGroup).order_by(RecipeGroup.name))
    return [_group_to_dict(g) for g in result.scalars()]


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
