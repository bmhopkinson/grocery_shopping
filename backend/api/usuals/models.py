from typing import Optional
from pydantic import BaseModel


class UsualCreateRequest(BaseModel):
    name: str
    category: Optional[str] = None


class UsualUpdateRequest(BaseModel):
    name: str
    category: Optional[str] = None


class AddUsualsToRemindersRequest(BaseModel):
    usual_ids: list[str]
    list_name: str


class AddUsualsToWorkingListRequest(BaseModel):
    usual_ids: list[str]
    working_list_id: str
