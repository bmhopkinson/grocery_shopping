"""
Nodes for the recipe extractor workflow.

Extracts metadata, ingredients, and directions from a recipe URL and saves to the database.
"""

import json
import logging

from agent.models import (
    RecipeExtractorState,
    ExtractedIngredients,
    RecipeMetadata,
    ExtractedDirections,
)
from agent.prompts import (
    get_extract_ingredients_prompt,
    get_extract_recipe_metadata_prompt,
    get_extract_directions_prompt,
)
from agent.nodes.base import create_http_client, invoke_structured
from agent.nodes.html_utils import extract_json_ld_recipe, extract_text_content


logger = logging.getLogger(__name__)


async def fetch_recipe_page(state: RecipeExtractorState) -> dict:
    """
    Fetch the recipe page HTML and extract any JSON-LD structured data.

    Reads: recipe_url
    Writes: raw_html, json_ld
    """
    url = state["recipe_url"]

    try:
        async with create_http_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"raw_html": None, "json_ld": None, "error": f"Failed to fetch recipe page: {e}"}

    json_ld = extract_json_ld_recipe(html)
    return {"raw_html": html, "json_ld": json_ld}


def extract_recipe_metadata(state: RecipeExtractorState) -> dict:
    """
    Extract recipe name, creator, and description.

    Tries JSON-LD structured data first, falls back to LLM extraction.

    Reads: json_ld, raw_html, recipe_url
    Writes: recipe_name, recipe_creator, recipe_notes
    """
    json_ld = state.get("json_ld")

    if json_ld:
        data = json.loads(json_ld)
        name = data.get("name")

        author = data.get("author") or data.get("creator")
        creator = None
        if isinstance(author, dict):
            creator = author.get("name")
        elif isinstance(author, list) and author:
            first = author[0]
            creator = first.get("name") if isinstance(first, dict) else str(first)
        elif isinstance(author, str):
            creator = author

        notes = data.get("description")

        image = data.get("image")
        if isinstance(image, list):
            image = image[0]
        if isinstance(image, dict):
            image = image.get("url")
        image_url = image if isinstance(image, str) else None

        if name:
            return {
                "recipe_name": name,
                "recipe_creator": creator,
                "recipe_notes": notes,
                "recipe_image_url": image_url,
            }

    raw_html = state.get("raw_html") or ""
    content = extract_text_content(raw_html)
    if len(content) > 15000:
        content = content[:15000]

    result: RecipeMetadata = invoke_structured(
        RecipeMetadata, get_extract_recipe_metadata_prompt(content, state["recipe_url"])
    )
    return {
        "recipe_name": result.name,
        "recipe_creator": result.creator,
        "recipe_notes": result.notes,
    }


def extract_recipe_ingredients_for_db(state: RecipeExtractorState) -> dict:
    """
    Extract ingredients from the recipe page.

    Reads: json_ld, raw_html
    Writes: extracted_ingredients
    """
    json_ld = state.get("json_ld")
    content = json_ld if json_ld else _truncated_text(state.get("raw_html") or "")

    result: ExtractedIngredients = invoke_structured(
        ExtractedIngredients, get_extract_ingredients_prompt(content)
    )
    return {"extracted_ingredients": result.ingredients}


def extract_recipe_directions(state: RecipeExtractorState) -> dict:
    """
    Extract step-by-step cooking directions.

    Tries JSON-LD recipeInstructions first, falls back to LLM extraction.

    Reads: json_ld, raw_html, recipe_name
    Writes: extracted_directions
    """
    json_ld = state.get("json_ld")

    if json_ld:
        data = json.loads(json_ld)
        instructions = data.get("recipeInstructions")
        if instructions:
            steps = []
            for step in instructions:
                if isinstance(step, str):
                    steps.append(step)
                elif isinstance(step, dict):
                    text = step.get("text") or step.get("name") or ""
                    if text:
                        steps.append(text)
            if steps:
                return {"extracted_directions": steps}

    content = _truncated_text(state.get("raw_html") or "")
    recipe_name = state.get("recipe_name") or ""

    result: ExtractedDirections = invoke_structured(
        ExtractedDirections, get_extract_directions_prompt(content, recipe_name)
    )
    return {"extracted_directions": result.directions}


async def save_recipe_to_db(state: RecipeExtractorState) -> dict:
    """
    Save the extracted recipe, ingredients, and directions to the database.

    Reads: recipe_name, recipe_url, recipe_creator, recipe_notes,
           extracted_ingredients, extracted_directions, recipe_image_url
    Writes: saved_recipe
    """
    from database import get_session
    import services.recipes as recipes_crud

    name = state.get("recipe_name") or "Untitled Recipe"
    url = state["recipe_url"]
    creator = state.get("recipe_creator")
    notes = state.get("recipe_notes")
    ingredients = state.get("extracted_ingredients") or []
    directions = state.get("extracted_directions") or []

    # Combine creator and description into notes field
    if creator and notes:
        full_notes = f"By {creator}. {notes}"
    elif creator:
        full_notes = f"By {creator}"
    else:
        full_notes = notes

    image_data = None
    image_content_type = None
    image_url = state.get("recipe_image_url")
    if image_url:
        try:
            async with create_http_client() as client:
                img_response = await client.get(image_url, timeout=5.0)
                img_response.raise_for_status()
                image_data = img_response.content
                image_content_type = img_response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        except Exception as e:
            logger.warning(f"Failed to download recipe image from {image_url}: {e}")

    async with get_session() as session:
        recipe = await recipes_crud.create_recipe(
            session, name, url, full_notes, directions,
            image_data=image_data, image_content_type=image_content_type,
        )
        recipe_id = recipe["id"]

        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                ing_name = ingredient.get("name", "")
                ing_amount = ingredient.get("amount") or None
                ing_unit = ingredient.get("unit") or None
            else:
                ing_name = ingredient.name
                ing_amount = ingredient.amount or None
                ing_unit = ingredient.unit or None

            if ing_name:
                await recipes_crud.add_recipe_ingredient(
                    session, recipe_id, ing_name, ing_amount, ing_unit
                )

    return {"saved_recipe": recipe}


def _truncated_text(html: str, max_chars: int = 30000) -> str:
    content = extract_text_content(html)
    return content[:max_chars] if len(content) > max_chars else content
