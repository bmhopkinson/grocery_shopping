from typing import Optional
from pydantic import BaseModel


class RecipeCreateRequest(BaseModel):
    name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    instructions: list[str] = []


class RecipeUpdateRequest(BaseModel):
    name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    instructions: list[str] = []


class RecipeIngredientCreateRequest(BaseModel):
    name: str
    amount: str = ""
    unit: str = ""


class RecipeIngredientUpdateRequest(BaseModel):
    name: str
    amount: str = ""
    unit: str = ""
