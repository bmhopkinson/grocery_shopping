import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from database import get_session
import services.recipes as recipes_crud
from agent.recipe_extractor import build_recipe_extractor_graph, EXTRACTOR_NODE_MESSAGES
from server.sse import sse_event, status_event, error_event
from .models import (
    RecipeCreateRequest,
    RecipeUpdateRequest,
    RecipeIngredientCreateRequest,
    RecipeIngredientUpdateRequest,
    RecipeExtractRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/recipes/extract-from-url")
async def extract_recipe_from_url(request: RecipeExtractRequest):
    """
    Extract a recipe from a URL using an agentic workflow and save it to the database.

    Returns an SSE stream with status events and a final 'recipe_extracted' event.
    """
    url = str(request.url)
    logger.info(f"POST /recipes/extract-from-url - url={url!r}")

    async def event_generator():
        graph = build_recipe_extractor_graph()
        initial_input = {
            "recipe_url": url,
            "raw_html": None,
            "json_ld": None,
            "recipe_name": None,
            "recipe_creator": None,
            "recipe_notes": None,
            "recipe_image_url": None,
            "extracted_ingredients": None,
            "extracted_directions": None,
            "saved_recipe": None,
            "error": None,
        }

        try:
            accumulated = {}
            async for updates in graph.astream(
                initial_input, config={"configurable": {}}, stream_mode="updates"
            ):
                for node_name, node_output in updates.items():
                    accumulated.update(node_output)
                    msg = EXTRACTOR_NODE_MESSAGES.get(node_name, "Processing...")
                    yield status_event(node_name, msg)

            if accumulated.get("error"):
                yield error_event(accumulated["error"])
                return

            saved_recipe = accumulated.get("saved_recipe")
            if saved_recipe:
                yield sse_event("recipe_extracted", {"recipe": saved_recipe})
            else:
                yield error_event("Recipe extraction completed but no recipe was saved")

        except Exception as e:
            logger.exception(f"Error extracting recipe from {url}: {e}")
            yield error_event(str(e))

    return EventSourceResponse(event_generator())


@router.get("/recipes/tags")
async def list_recipe_tags():
    async with get_session() as session:
        return await recipes_crud.get_all_tags(session)


@router.get("/recipes")
async def list_recipes(
    group_id: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    async with get_session() as session:
        if group_id is not None or tags or offset > 0:
            return await recipes_crud.get_recipes_paginated(session, group_id, tags or [], offset, limit)
        return await recipes_crud.get_recipes(session)


@router.post("/recipes")
async def create_recipe(request: RecipeCreateRequest):
    async with get_session() as session:
        return await recipes_crud.create_recipe(
            session, request.name, request.url, request.notes, request.instructions,
            group_id=request.group_id, tags=request.tags or None,
        )


@router.get("/recipes/{recipe_id}/image")
async def get_recipe_image(recipe_id: str):
    async with get_session() as session:
        result = await recipes_crud.get_recipe_image(session, recipe_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No image for this recipe")
    image_data, content_type = result
    return Response(content=image_data, media_type=content_type)


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
            session, recipe_id, request.name, request.url, request.notes, request.instructions,
            group_id=request.group_id, tags=request.tags or None,
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
