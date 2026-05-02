from pydantic import BaseModel


class GroupCreateRequest(BaseModel):
    name: str
