from fastapi import APIRouter, Request
from fastapi.responses import Response
import json, os, base64

router = APIRouter(prefix="/canvas")
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "canvas_state.json")
PNG_FILE   = os.path.join(os.path.dirname(__file__), "..", "canvas_snapshot.png")

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

@router.get("/png")
async def get_png():
    if not os.path.exists(PNG_FILE):
        return Response(status_code=204)
    with open(PNG_FILE, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/png")

@router.post("/png")
async def save_png(request: Request):
    body = await request.json()
    png_bytes = base64.b64decode(body["data"])
    with open(PNG_FILE, "wb") as f:
        f.write(png_bytes)
    return {"ok": True}
