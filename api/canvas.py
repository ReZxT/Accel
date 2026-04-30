from fastapi import APIRouter
import json, os

router = APIRouter(prefix="/canvas")
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "canvas_state.json")

@router.get("/state")
async def get_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

@router.post("/state")
async def save_state(body: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(body, f)
    return {"ok": True}
