import logging

from fastapi import APIRouter, HTTPException

from database import get_session
import services.recipes as recipes_crud
from .models import (
    RecipeCreateRequest,
    RecipeUpdateRequest,
    RecipeIngredientCreateRequest,
    RecipeIngredientUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recipes")
async def list_recipes():
    async with get_session() as session:
        return await recipes_crud.get_recipes(session)


@router.post("/recipes")
async def create_recipe(request: RecipeCreateRequest):
    async with get_session() as session:
        return await recipes_crud.create_recipe(
            session, request.name, request.url, request.notes, request.instructions
        )


@router.get("/recipes/{recipe_id}")
async def get_recipe(recipe_id: str):
    async with get_session() as session:
        recipe = await recipes_crud.get_recipe(session, recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        ingredients = await recipes_crud.get_recipe_ingredients(session, recipe_id)
    recipe["ingredients"] = ingredients
    return recipe


@router.put("/recipes/{recipe_id}")
async def update_recipe(recipe_id: str, request: RecipeUpdateRequest):
    async with get_session() as session:
        recipe = await recipes_crud.update_recipe(
            session, recipe_id, request.name, request.url, request.notes, request.instructions
        )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str):
    async with get_session() as session:
        deleted = await recipes_crud.delete_recipe(session, recipe_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"deleted": True}


@router.get("/recipes/{recipe_id}/ingredients")
async def list_recipe_ingredients(recipe_id: str):
    async with get_session() as session:
        return await recipes_crud.get_recipe_ingredients(session, recipe_id)


@router.post("/recipes/{recipe_id}/ingredients")
async def add_recipe_ingredient(recipe_id: str, request: RecipeIngredientCreateRequest):
    async with get_session() as session:
        return await recipes_crud.add_recipe_ingredient(
            session, recipe_id, request.name, request.amount, request.unit
        )


@router.put("/recipes/{recipe_id}/ingredients/{ingredient_id}")
async def update_recipe_ingredient(recipe_id: str, ingredient_id: str, request: RecipeIngredientUpdateRequest):
    async with get_session() as session:
        ingredient = await recipes_crud.update_recipe_ingredient(
            session, ingredient_id, request.name, request.amount, request.unit
        )
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.delete("/recipes/{recipe_id}/ingredients/{ingredient_id}")
async def delete_recipe_ingredient(recipe_id: str, ingredient_id: str):
    async with get_session() as session:
        deleted = await recipes_crud.delete_recipe_ingredient(session, ingredient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return {"deleted": True}
