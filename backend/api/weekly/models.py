from typing import Optional
from pydantic import BaseModel


class MealCreateRequest(BaseModel):
    name: str
    day_of_week: int
    week_start: str
    notes: Optional[str] = None
    url: Optional[str] = None


class MealUpdateRequest(BaseModel):
    name: str
    day_of_week: int
    notes: Optional[str] = None
    url: Optional[str] = None
