"""
Prompt templates for the Meal Planner agent.
"""


def get_parse_recipes_prompt(cuisine: str, search_results: str) -> str:
    """Prompt for parsing search results into structured recipes."""
    return f"""Based on these search results about {cuisine} recipes, extract exactly 5 recipes WITH their URLs.

Search Results:
{search_results}

Only include recipes where you can find a valid URL in the search results."""


def get_validate_recipes_prompt(recipes_text: str, cuisine: str) -> str:
    """Prompt for validating recipe URLs."""
    return f"""Analyze these recipe URLs and determine which ones are SINGLE RECIPE pages vs COLLECTION/AGGREGATOR pages.

Recipes to analyze:
{recipes_text}

For each recipe, determine if the URL points to:
- SINGLE: A page with ONE specific recipe (with ingredients and instructions)
- COLLECTION: A page with multiple recipes, a recipe roundup, Pinterest board, or general site homepage

IMPORTANT indicators of COLLECTION pages (mark as invalid):
- Pinterest URLs (pinterest.com)
- URLs ending in just the domain (e.g., allrecipes.com/ with no path)
- URLs containing words like "ideas", "collection", "roundup", "best-recipes"
- TikTok videos (usually not detailed recipes)
- URLs with generic paths like "/recipes" or "/category/"

Return only the recipes that are SINGLE recipe pages, and suggest 5 specific {cuisine} dish names to search for if we need more recipes."""


def get_dish_names_prompt(cuisine: str) -> str:
    """Prompt for generating dish name suggestions."""
    return f"List 5 specific popular {cuisine} dinner dish names."


def get_refine_search_prompt(combined_results: str, sources: list[str] = None) -> str:
    """Prompt for parsing refined search results."""
    if sources:
        sources_text = ", ".join(sources)
        prefer_line = f"Prefer URLs from: {sources_text}"
    else:
        prefer_line = "Include recipes from any reputable cooking website."

    return f"""Extract specific recipes from these search results. Each result is for a specific dish.

Search Results:
{combined_results}

ONLY include URLs that point to a SINGLE RECIPE PAGE (not collections or homepages).
{prefer_line}"""


def get_refine_search_query(dish: str, sources: list[str] = None) -> str:
    """Query template for refined recipe searches."""
    if sources:
        site_filters = " OR ".join(f"site:{s}" for s in sources[:4])  # Limit to 4 sites for query length
        return f"{dish} recipe {site_filters}"
    return f"{dish} recipe"


def get_extract_recipe_metadata_prompt(content: str, url: str) -> str:
    """Prompt for extracting recipe name, creator, and description from page content."""
    return f"""Extract metadata from this recipe page.

URL: {url}

Page content:
{content}

Extract:
1. Recipe name - the specific dish name (not the website name)
2. Creator/author - the person or publication who created this recipe (null if not found)
3. Notes - a brief 1-2 sentence description of the dish (null if not found)"""


def get_extract_directions_prompt(content: str, recipe_name: str) -> str:
    """Prompt for extracting step-by-step cooking instructions."""
    return f"""Extract the step-by-step cooking instructions for "{recipe_name}" from this recipe page.

Page content:
{content}

Return each step as a complete sentence in the correct order. Include all preparation and cooking steps. Do not include ingredient quantities in the steps."""


def get_extract_ingredients_prompt(recipe_content: str) -> str:
    """Prompt for extracting ingredients from recipe page content."""
    return f"""Extract all ingredients from this recipe page. For each ingredient, identify:
1. The ingredient name (just the food item, not preparation instructions like "diced" or "minced")
2. The amount/quantity (e.g., "2", "1/2", "1-2")
3. The unit of measurement (e.g., "cups", "tablespoons", "pounds", or empty string if no unit)

Recipe content:
{recipe_content}

Extract ONLY the ingredients list. Do not include equipment, garnishes marked as optional, or serving suggestions."""
