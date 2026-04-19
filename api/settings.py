from fastapi import APIRouter
from pydantic import BaseModel
from memory.profile import get_tool_settings, save_tool_settings

router = APIRouter()


class ToolSettingsPayload(BaseModel):
    tool_settings: dict[str, str]


@router.get("/settings/tools")
async def get_settings():
    return {"tool_settings": await get_tool_settings()}


@router.put("/settings/tools")
async def update_settings(body: ToolSettingsPayload):
    await save_tool_settings(body.tool_settings)
    return {"status": "ok"}
