import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Recipe, RecipeIngredient


def _recipe_to_dict(r: Recipe) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "url": r.url,
        "notes": r.notes,
        "instructions": r.instructions or [],
        "group_id": str(r.group_id) if r.group_id else None,
        "group": {"id": str(r.group.id), "name": r.group.name} if r.group else None,
        "created_at": r.created_at.isoformat(),
    }


def _ingredient_to_dict(i: RecipeIngredient) -> dict:
    return {
        "id": str(i.id),
        "recipe_id": str(i.recipe_id),
        "name": i.name,
        "amount": i.amount or "",
        "unit": i.unit or "",
        "position": i.position,
    }


async def get_recipes(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(Recipe).order_by(Recipe.name))
    return [_recipe_to_dict(r) for r in result.scalars()]


async def get_recipe(session: AsyncSession, recipe_id: str) -> Optional[dict]:
    result = await session.execute(select(Recipe).where(Recipe.id == uuid.UUID(recipe_id)))
    r = result.scalar_one_or_none()
    return _recipe_to_dict(r) if r else None


async def create_recipe(
    session: AsyncSession,
    name: str,
    url: Optional[str],
    notes: Optional[str],
    instructions: list,
    image_data: Optional[bytes] = None,
    image_content_type: Optional[str] = None,
    group_id: Optional[uuid.UUID] = None,
) -> dict:
    recipe = Recipe(
        name=name,
        url=url,
        notes=notes,
        instructions=instructions,
        image_data=image_data,
        image_content_type=image_content_type,
        group_id=group_id,
    )
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)
    return _recipe_to_dict(recipe)


async def update_recipe(
    session: AsyncSession,
    recipe_id: str,
    name: str,
    url: Optional[str],
    notes: Optional[str],
    instructions: list,
    group_id: Optional[uuid.UUID] = None,
) -> Optional[dict]:
    result = await session.execute(select(Recipe).where(Recipe.id == uuid.UUID(recipe_id)))
    recipe = result.scalar_one_or_none()
    if not recipe:
        return None
    recipe.name = name
    recipe.url = url
    recipe.notes = notes
    recipe.instructions = instructions
    recipe.group_id = group_id
    await session.commit()
    await session.refresh(recipe)
    return _recipe_to_dict(recipe)


async def delete_recipe(session: AsyncSession, recipe_id: str) -> bool:
    result = await session.execute(select(Recipe).where(Recipe.id == uuid.UUID(recipe_id)))
    recipe = result.scalar_one_or_none()
    if not recipe:
        return False
    await session.delete(recipe)
    await session.commit()
    return True


async def get_recipe_ingredients(session: AsyncSession, recipe_id: str) -> list[dict]:
    result = await session.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == uuid.UUID(recipe_id))
        .order_by(RecipeIngredient.position, RecipeIngredient.created_at)
    )
    return [_ingredient_to_dict(i) for i in result.scalars()]


async def add_recipe_ingredient(
    session: AsyncSession,
    recipe_id: str,
    name: str,
    amount: Optional[str],
    unit: Optional[str],
) -> dict:
    result = await session.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == uuid.UUID(recipe_id))
        .order_by(RecipeIngredient.position.desc())
    )
    existing = result.scalars().all()
    position = (existing[0].position + 1) if existing else 0

    ingredient = RecipeIngredient(
        recipe_id=uuid.UUID(recipe_id),
        name=name,
        amount=amount or None,
        unit=unit or None,
        position=position,
    )
    session.add(ingredient)
    await session.commit()
    await session.refresh(ingredient)
    return _ingredient_to_dict(ingredient)


async def update_recipe_ingredient(
    session: AsyncSession,
    ingredient_id: str,
    name: str,
    amount: Optional[str],
    unit: Optional[str],
) -> Optional[dict]:
    result = await session.execute(
        select(RecipeIngredient).where(RecipeIngredient.id == uuid.UUID(ingredient_id))
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        return None
    ingredient.name = name
    ingredient.amount = amount or None
    ingredient.unit = unit or None
    await session.commit()
    await session.refresh(ingredient)
    return _ingredient_to_dict(ingredient)


async def delete_recipe_ingredient(session: AsyncSession, ingredient_id: str) -> bool:
    result = await session.execute(
        select(RecipeIngredient).where(RecipeIngredient.id == uuid.UUID(ingredient_id))
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        return False
    await session.delete(ingredient)
    await session.commit()
    return True


async def get_recipe_image(
    session: AsyncSession, recipe_id: str
) -> Optional[tuple[bytes, str]]:
    result = await session.execute(select(Recipe).where(Recipe.id == uuid.UUID(recipe_id)))
    r = result.scalar_one_or_none()
    if not r or not r.image_data:
        return None
    return (r.image_data, r.image_content_type or "image/jpeg")
