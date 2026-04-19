from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tools.approval import resolve

router = APIRouter()


class ApprovalResponse(BaseModel):
    approved: bool


@router.post("/approve/{request_id}")
async def approve(request_id: str, body: ApprovalResponse):
    ok = resolve(request_id, body.approved)
    if not ok:
        raise HTTPException(status_code=404, detail="Request not found or already resolved")
    return {"status": "resolved", "approved": body.approved}
