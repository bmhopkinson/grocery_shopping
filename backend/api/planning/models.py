from typing import Union
from pydantic import BaseModel


class PlanRequest(BaseModel):
    cuisine_type: str = ""
    direct_url: str = ""
    preferred_sources: list[str] = []


class ResumeRequest(BaseModel):
    input: Union[str, dict]
