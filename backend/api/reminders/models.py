from pydantic import BaseModel


class ReorderRemindersRequest(BaseModel):
    list_name: str
