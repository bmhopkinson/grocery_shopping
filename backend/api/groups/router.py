from fastapi import APIRouter, HTTPException

from database import get_session
import services.groups as groups_crud
from .models import GroupCreateRequest

router = APIRouter()


@router.get("/groups")
async def list_groups():
    async with get_session() as session:
        return await groups_crud.get_groups(session)


@router.post("/groups", status_code=201)
async def create_group(request: GroupCreateRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Group name cannot be empty")
    async with get_session() as session:
        existing = await groups_crud.get_group_by_name(session, name)
        if existing:
            return existing
        return await groups_crud.create_group(session, name)


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str):
    async with get_session() as session:
        deleted = await groups_crud.delete_group(session, group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"deleted": True}
