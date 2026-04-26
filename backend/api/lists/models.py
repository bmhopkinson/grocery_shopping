from pydantic import BaseModel


class WorkingListCreateRequest(BaseModel):
    name: str


class WorkingListItemCreateRequest(BaseModel):
    name: str
    amount: str = ""
    unit: str = ""


class WorkingListItemUpdateRequest(BaseModel):
    name: str
    amount: str = ""
    unit: str = ""


class WorkingListReorderRequest(BaseModel):
    item_ids: list[str]


class WorkingListDumpRequest(BaseModel):
    list_name: str
