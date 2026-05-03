from typing import Optional
from uuid import UUID
from pydantic import BaseModel, AnyHttpUrl


class RecipeCreateRequest(BaseModel):
    name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    instructions: list[str] = []
    tags: list[str] = []
    group_id: Optional[UUID] = None


class RecipeUpdateRequest(BaseModel):
    name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    instructions: list[str] = []
    tags: list[str] = []
    group_id: Optional[UUID] = None


class RecipeIngredientCreateRequest(BaseModel):
    name: str
    amount: str = ""
    unit: str = ""


class RecipeIngredientUpdateRequest(BaseModel):
    name: str
    amount: str = ""
    unit: str = ""


class RecipeExtractRequest(BaseModel):
    url: AnyHttpUrl
