"""
Data models and state definitions for the Meal Planner agent.
"""

from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field


# Structured output models for LLM responses

class Recipe(BaseModel):
    """A single recipe extracted from search results."""
    name: str = Field(description="The recipe/meal name")
    description: str = Field(description="Brief 1-sentence description of the dish")
    url: str = Field(description="The full URL to the recipe page")


class ParsedRecipes(BaseModel):
    """Collection of recipes parsed from search results."""
    recipes: List[Recipe] = Field(description="List of exactly 5 recipes with URLs")


class ValidationResult(BaseModel):
    """Result of validating recipe URLs."""
    valid_recipes: List[Recipe] = Field(
        description="Recipes that point to single recipe pages (not collections)"
    )
    dish_names: List[str] = Field(
        description="5 specific dish names to search for if more recipes are needed"
    )


class DishNames(BaseModel):
    """List of dish names for a cuisine."""
    dishes: List[str] = Field(description="List of 5 specific popular dinner dish names")


class MealOption(BaseModel):
    """A meal option presented to the user for selection."""
    id: int = Field(description="Selection number for the option")
    name: str = Field(description="The recipe/meal name")
    description: str = Field(description="Brief description of the dish")
    recipe_url: str = Field(description="The full URL to the recipe page")


class Ingredient(BaseModel):
    """A single ingredient with amount and unit."""
    name: str = Field(description="The ingredient name (e.g., 'chicken breast', 'olive oil')")
    amount: str = Field(description="The quantity (e.g., '2', '1/2', '1-2')")
    unit: str = Field(description="The unit of measurement (e.g., 'cups', 'tablespoons', 'pounds', or empty string if none)")


class ExtractedIngredients(BaseModel):
    """Collection of ingredients extracted from a recipe."""
    ingredients: List[Ingredient] = Field(description="List of ingredients with amounts and units")


# Graph state definition

class MealPlannerState(TypedDict):
    """State for the meal planner graph."""
    # Entry mode
    direct_url: Optional[str]  # Direct recipe URL (skips search flow)

    # Search-related fields
    cuisine_type: str
    preferred_sources: Optional[List[str]]
    search_results: Optional[str]
    meal_options: Optional[List[MealOption]]

    # Shared fields
    selected_meal: Optional[MealOption]
    messages: List
    refinement_count: int
    refine_dishes: Optional[List[str]]

    # Meal processing fields
    grocery_list: Optional[List[Ingredient]]
    reminders_added: Optional[bool]
