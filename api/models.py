"""Model management API — list, get, and switch models at runtime."""

from fastapi import APIRouter
from pydantic import BaseModel
from models.registry import registry

router = APIRouter(prefix="/models", tags=["models"])


class SetModelRequest(BaseModel):
    role: str = "chat"           # "chat" | "curator" | "embeddings"
    model_id: str


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int
    capabilities: list[str]
    supports_thinking: bool
    supports_vision: bool


@router.get("")
async def list_models():
    """List all available models and current active selections."""
    state = registry.active_state()
    # Convert available models to clean format
    state["available"] = [
        {
            "id": m["id"],
            "name": m["name"],
            "provider": m["provider"],
            "context_window": m["context_window"],
            "capabilities": m["capabilities"],
            "supports_thinking": m["supports_thinking"],
            "supports_vision": m["supports_vision"],
        }
        for m in state["available"]
    ]
    return state


@router.put("/active")
async def set_active_model(body: SetModelRequest):
    """Switch the active model for a role."""
    if body.role == "chat":
        registry.set_active_chat(body.model_id)
    elif body.role == "curator":
        registry.set_active_curator(body.model_id)
    elif body.role == "embeddings":
        registry.set_active_embeddings(body.model_id)
    else:
        return {"error": f"Unknown role: {body.role}"}, 400

    return {"status": "ok", "role": body.role, "model_id": body.model_id}


@router.get("/active")
async def get_active_models():
    """Get just the active model IDs for each role."""
    return {
        "chat": registry.chat.id,
        "curator": registry.curator.id,
        "embeddings": registry.embeddings.id,
        "chat_details": {
            "name": registry.chat.name,
            "provider": registry.chat.provider,
            "supports_thinking": registry.chat.supports_thinking,
            "supports_vision": registry.chat.supports_vision,
            "context_window": registry.chat.context_window,
        },
    }
