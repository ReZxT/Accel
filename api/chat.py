import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from router.classifier import classify
from router.tier0 import classify_tier0
from agents.chat_agent import run_chat
from models.registry import registry

router = APIRouter()

# per-session cancel events — set to signal the agentic loop to stop
_cancel_events: dict[str, asyncio.Event] = {}


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
    voice_mode: bool = False
    model_id: str | None = None
    thinking_enabled: bool | None = None  # explicit override: True=force think, False=force non-think, None=model default


async def _event_stream(chat_req: ChatRequest, http_req: Request):
    images = [i.model_dump() for i in chat_req.images] if chat_req.images else None
    files = [f.model_dump() for f in chat_req.files] if chat_req.files else None

    cancel = asyncio.Event()
    _cancel_events[chat_req.sessionId] = cancel

    try:
        # Tier 0: fast rule-based classification — may short-circuit entirely
        tier0 = classify_tier0(chat_req.chatInput, has_images=bool(images), has_files=bool(files))

        if tier0 and tier0.canned_response:
            yield f"data: {json.dumps({'type': 'route', 'route': {'tier0': tier0.intent}})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'text': tier0.canned_response})}\n\n"
            return

        route = await classify(chat_req.chatInput, images=images, files=files)

        # emit route decision so UI/debug can see it
        yield f"data: {json.dumps({'type': 'route', 'route': route.__dict__})}\n\n"

        if route.route_family == "direct_chat":
            gen = run_chat(
                chat_input=chat_req.chatInput,
                chat_history=chat_req.chatHistory,
                session_id=chat_req.sessionId,
                route=route,
                voice_mode=chat_req.voice_mode,
                cancel=cancel,
                tier0=tier0,
                model_id=chat_req.model_id,
                thinking_enabled=chat_req.thinking_enabled,
            )

        elif route.route_family == "multimodal":
            gen = run_chat(
                chat_input=chat_req.chatInput,
                chat_history=chat_req.chatHistory,
                session_id=chat_req.sessionId,
                images=images,
                route=route,
                voice_mode=chat_req.voice_mode,
                cancel=cancel,
                tier0=tier0,
                model_id=chat_req.model_id,
                thinking_enabled=chat_req.thinking_enabled,
            )

        elif route.route_family == "preprocessed_text":
            from agents.preprocessed_agent import run_preprocessed
            gen = run_preprocessed(
                chat_input=chat_req.chatInput,
                files=files,
                chat_history=chat_req.chatHistory,
                session_id=chat_req.sessionId,
                route=route,
            )

        else:
            yield f"data: {json.dumps({'type': 'error', 'text': f'Unknown route: {route.route_family}'})}\n\n"
            return

        async for chunk in gen:
            if await http_req.is_disconnected() or cancel.is_set():
                break
            yield f"data: {chunk}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
    finally:
        _cancel_events.pop(chat_req.sessionId, None)
        yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(chat_req: ChatRequest, http_req: Request):
    return StreamingResponse(
        _event_stream(chat_req, http_req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/cancel")
async def cancel(session_id: str = "default"):
    event = _cancel_events.get(session_id)
    if event:
        event.set()
        return {"status": "cancelled", "session_id": session_id}
    return {"status": "no_active_request", "session_id": session_id}


@router.get("/health")
async def health():
    from circuit_breaker import all_status
    return {"status": "ok", "service": "bootstrap", "circuits": all_status()}


@router.get("/status/circuits")
async def circuit_status():
    from circuit_breaker import all_status
    return all_status()


@router.post("/command")
async def handle_command(body: dict):
    """Handle slash commands from the UI.

    Returns structured result that the UI can use to update state.
    Supported commands: /model <id>, /personality <name>, /voice on|off,
    /clear, /cancel, /context, /status.
    """
    cmd = (body.get("command") or body.get("chatInput", "")).strip()
    if not cmd.startswith("/"):
        return {"error": "not a command"}

    parts = cmd[1:].split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if action == "model":
        if not arg:
            available = [m["id"] for m in registry.active_state()["available"]]
            return {
                "type": "model_list",
                "models": available,
                "active": registry.chat.id,
                "message": f"Active: {registry.chat.name}. Available: {', '.join(available)}",
            }
        try:
            registry.set_active_chat(arg)
            return {
                "type": "model_switched",
                "model_id": registry.chat.id,
                "model_name": registry.chat.name,
                "message": f"Switched to {registry.chat.name}",
            }
        except Exception:
            return {"type": "error", "message": f"Unknown model: {arg}"}

    elif action == "personality":
        return {
            "type": "info",
            "message": "Personality switching via /personality not yet implemented. Use the preflight system.",
        }

    elif action == "voice":
        if arg.lower() in ("on", "true", "1"):
            from api.voice import _voice_enabled
            return {"type": "voice_toggle", "enabled": True}
        elif arg.lower() in ("off", "false", "0"):
            return {"type": "voice_toggle", "enabled": False}
        return {"type": "info", "message": "Usage: /voice on|off"}

    elif action == "status":
        from circuit_breaker import all_status
        state = registry.active_state()
        return {
            "type": "status",
            "model": f"{registry.chat.name} ({registry.chat.provider})",
            "circuits": all_status(),
        }

    elif action == "context":
        return {
            "type": "context",
            "model": f"{registry.chat.name} ({registry.chat.provider})",
            "context_window": registry.chat.context_window,
            "supports_thinking": registry.chat.supports_thinking,
            "supports_vision": registry.chat.supports_vision,
        }

    else:
        return {"type": "unknown", "command": action, "message": f"Unknown command: /{action}"}
