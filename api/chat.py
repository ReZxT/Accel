import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from router.classifier import classify
from agents.chat_agent import run_chat

router = APIRouter()


class ImagePayload(BaseModel):
    base64: str
    name: str
    type: str


class FilePayload(BaseModel):
    content: str
    name: str
    language: str = ""


class ChatRequest(BaseModel):
    chatInput: str
    chatHistory: list[dict] = []
    sessionId: str = "default"
    images: list[ImagePayload] = []
    files: list[FilePayload] = []


async def _event_stream(request: ChatRequest):
    images = [i.model_dump() for i in request.images] if request.images else None
    files = [f.model_dump() for f in request.files] if request.files else None

    try:
        route = await classify(request.chatInput, images=images, files=files)

        # emit route decision so UI/debug can see it
        yield f"data: {json.dumps({'type': 'route', 'route': route.__dict__})}\n\n"

        if route.route_family == "direct_chat":
            gen = run_chat(
                chat_input=request.chatInput,
                chat_history=request.chatHistory,
                session_id=request.sessionId,
                route=route,
            )

        elif route.route_family == "multimodal":
            gen = run_chat(
                chat_input=request.chatInput,
                chat_history=request.chatHistory,
                session_id=request.sessionId,
                images=images,
                route=route,
            )

        elif route.route_family == "preprocessed_text":
            from agents.preprocessed_agent import run_preprocessed
            gen = run_preprocessed(
                chat_input=request.chatInput,
                files=files,
                chat_history=request.chatHistory,
                session_id=request.sessionId,
                route=route,
            )

        else:
            yield f"data: {json.dumps({'type': 'error', 'text': f'Unknown route: {route.route_family}'})}\n\n"
            return

        async for chunk in gen:
            yield f"data: {chunk}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "bootstrap"}
