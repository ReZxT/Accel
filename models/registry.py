"""Model registry — defines available models and tracks active selections.

ModelDef holds everything needed to call a model: provider, endpoint,
credentials, capabilities, and provider-specific parameters.

The registry is a singleton that holds all model defs and tracks which
one is active for each role (chat / curator / embeddings).
"""

from dataclasses import dataclass, field
from typing import Optional
import os
import json
import logging

log = logging.getLogger(__name__)

# API keys config file — survives process restarts, works regardless of how bootstrap is launched
_API_KEYS_PATH = os.path.expanduser("~/.config/accel/api_keys.json")


def _read_key_from_file(key_name: str) -> str:
    """Read an API key from ~/.config/accel/api_keys.json as fallback."""
    try:
        if os.path.exists(_API_KEYS_PATH):
            with open(_API_KEYS_PATH) as f:
                data = json.load(f)
            return data.get(key_name, "")
    except Exception:
        pass
    return ""


@dataclass
class ModelDef:
    """Definition of a single model that can be used for inference."""

    id: str                          # stable key: "qwen-9b", "gpt-4o", "claude-sonnet"
    name: str                        # display name: "Qwen3.5 9B (local)"
    provider: str                    # "llama_cpp" | "openai" | "anthropic"
    model_name: str                  # name the API expects: "accel", "gpt-4o", "claude-sonnet-4-20250514"
    endpoint: str                    # base URL (can be localhost or api.openai.com)
    api_key: str = ""                # resolved from env or set directly
    api_key_env: str = ""            # env var to source api_key from, e.g. "OPENAI_API_KEY"

    # Capabilities
    capabilities: set = field(default_factory=lambda: {"chat"})
    context_window: int = 65536
    supports_streaming: bool = True
    supports_thinking: bool = False
    supports_vision: bool = False

    # Provider-specific args injected into every request
    extra_body: dict = field(default_factory=dict)
    extra_headers: dict = field(default_factory=dict)

    def resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            key = os.getenv(self.api_key_env, "")
            if key:
                return key
        # Fallback: read from ~/.config/accel/api_keys.json
        return _read_key_from_file(self.api_key_env)

    @property
    def auth_header(self) -> dict:
        key = self.resolve_api_key()
        if not key:
            return {}
        if self.provider == "anthropic":
            return {"x-api-key": key}
        return {"Authorization": f"Bearer {key}"}


# ---------------------------------------------------------------------------
# Built-in model definitions
# ---------------------------------------------------------------------------

DEFAULT_MODELS: list[ModelDef] = [
    ModelDef(
        id="qwen-9b",
        name="Qwen3.5 9B (local GPU)",
        provider="llama_cpp",
        model_name="accel",
        endpoint=os.getenv("CHAT_URL", "http://localhost:8080/v1"),
        capabilities={"chat", "vision", "thinking"},
        context_window=65536,
        supports_thinking=True,
        supports_vision=True,
    ),
    ModelDef(
        id="qwen-0.8b",
        name="Qwen3.5 0.8B (local CPU)",
        provider="llama_cpp",
        model_name="curator",
        endpoint=os.getenv("CURATOR_URL", "http://localhost:8082/v1"),
        context_window=8192,
    ),
    ModelDef(
        id="bge-m3",
        name="BGE-M3 (local CPU)",
        provider="llama_cpp",
        model_name="embed",
        endpoint=os.getenv("EMBED_URL", "http://localhost:8081/v1"),
        context_window=8192,
    ),
    ModelDef(
        id="gpt-4o",
        name="GPT-4o (OpenAI)",
        provider="openai",
        model_name="gpt-4o",
        endpoint="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        capabilities={"chat", "vision"},
        context_window=128000,
        supports_thinking=False,
        supports_vision=True,
    ),
    ModelDef(
        id="gpt-4.1",
        name="GPT-4.1 (OpenAI)",
        provider="openai",
        model_name="gpt-4.1",
        endpoint="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        capabilities={"chat", "vision"},
        context_window=1000000,
        supports_vision=True,
    ),
    ModelDef(
        id="deepseek-v4",
        name="DeepSeek V4 Pro",
        provider="openai",
        model_name="deepseek-chat",
        endpoint="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        capabilities={"chat", "thinking"},
        context_window=128000,
        supports_thinking=True,
        supports_vision=False,
    ),
    ModelDef(
        id="deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        provider="openai",
        model_name="deepseek-chat",
        endpoint="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        capabilities={"chat", "thinking"},
        context_window=128000,
        supports_thinking=True,
        supports_vision=False,
        extra_body={"model": "deepseek-chat"},  # will be overridden by backend
        extra_headers={"x-deepseek-model-type": "flash"},
    ),
    ModelDef(
        id="deepseek-reasoner",
        name="DeepSeek Reasoner (R1)",
        provider="openai",
        model_name="deepseek-reasoner",
        endpoint="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        capabilities={"chat", "thinking"},
        context_window=65536,
        supports_thinking=True,
        supports_vision=False,
    ),
    ModelDef(
        id="claude-sonnet",
        name="Claude Sonnet 4 (Anthropic)",
        provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        endpoint="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        capabilities={"chat", "vision", "thinking"},
        context_window=200000,
        supports_thinking=True,
        supports_vision=True,
    ),
]

# Models that can be resolved from env vars at startup
# Example: CHAT_MODEL_ID=gpt-4o overrides the active chat model
# Example: CHAT_MODEL_CUSTOM='{"id":"my-model","name":"Custom","provider":"llama_cpp",...}'


class ModelRegistry:
    """Singleton registry of available models and active selections."""

    def __init__(self):
        self._models: dict[str, ModelDef] = {}
        self._active_chat: str = ""
        self._active_curator: str = ""
        self._active_embeddings: str = ""

    def register(self, model: ModelDef):
        self._models[model.id] = model
        log.info("registered model: %s (%s)", model.id, model.provider)

    def register_all(self, models: list[ModelDef]):
        for m in models:
            self._models[m.id] = m

    def load_defaults(self):
        """Load built-in models, then apply env-var overrides for active selection."""
        self.register_all(DEFAULT_MODELS)

        # Apply env-var overrides for active models
        chat_id = os.getenv("CHAT_MODEL_ID", os.getenv("CHAT_MODEL", "qwen-9b"))
        curator_id = os.getenv("CURATOR_MODEL_ID", os.getenv("CURATOR_MODEL", "qwen-0.8b"))
        embed_id = os.getenv("EMBED_MODEL_ID", os.getenv("EMBED_MODEL", "bge-m3"))

        # Support custom models defined via env var
        custom_json = os.getenv("CUSTOM_MODELS", "")
        if custom_json:
            import json
            try:
                custom_list = json.loads(custom_json)
                for raw in custom_list:
                    raw["capabilities"] = set(raw.get("capabilities", ["chat"]))
                    self.register(ModelDef(**raw))
            except Exception:
                log.warning("failed to parse CUSTOM_MODELS env var")

        self.set_active_chat(chat_id)
        self.set_active_curator(curator_id)
        self.set_active_embeddings(embed_id)

    # -- active selection ---------------------------------------------------

    def set_active_chat(self, model_id: str):
        if model_id not in self._models:
            log.warning("unknown chat model %s — keeping %s", model_id, self._active_chat)
            return
        self._active_chat = model_id
        log.info("active chat model: %s (%s)", model_id, self._models[model_id].provider)

    def set_active_curator(self, model_id: str):
        if model_id not in self._models:
            log.warning("unknown curator model %s — keeping %s", model_id, self._active_curator)
            return
        self._active_curator = model_id
        log.info("active curator model: %s (%s)", model_id, self._models[model_id].provider)

    def set_active_embeddings(self, model_id: str):
        if model_id not in self._models:
            log.warning("unknown embeddings model %s — keeping %s", model_id, self._active_embeddings)
            return
        self._active_embeddings = model_id
        log.info("active embeddings model: %s (%s)", model_id, self._models[model_id].provider)

    @property
    def chat(self) -> ModelDef:
        return self._models.get(self._active_chat, self._models.get("qwen-9b", DEFAULT_MODELS[0]))

    @property
    def curator(self) -> ModelDef:
        return self._models.get(self._active_curator, self._models.get("qwen-0.8b", DEFAULT_MODELS[1]))

    @property
    def embeddings(self) -> ModelDef:
        return self._models.get(self._active_embeddings, self._models.get("bge-m3", DEFAULT_MODELS[2]))

    # -- queries ------------------------------------------------------------

    def get(self, model_id: str) -> ModelDef | None:
        return self._models.get(model_id)

    def list_all(self) -> list[ModelDef]:
        return sorted(self._models.values(), key=lambda m: m.name)

    def list_chat_models(self) -> list[ModelDef]:
        return [m for m in self._models.values() if "chat" in m.capabilities]

    def active_state(self) -> dict:
        return {
            "chat_model_id": self._active_chat,
            "curator_model_id": self._active_curator,
            "embeddings_model_id": self._active_embeddings,
            "chat": {
                "id": self.chat.id,
                "name": self.chat.name,
                "provider": self.chat.provider,
                "context_window": self.chat.context_window,
                "supports_thinking": self.chat.supports_thinking,
                "supports_vision": self.chat.supports_vision,
            },
            "curator": {
                "id": self.curator.id,
                "name": self.curator.name,
                "provider": self.curator.provider,
            },
            "embeddings": {
                "id": self.embeddings.id,
                "name": self.embeddings.name,
                "provider": self.embeddings.provider,
            },
            "available": [
                {
                    "id": m.id,
                    "name": m.name,
                    "provider": m.provider,
                    "context_window": m.context_window,
                    "capabilities": sorted(m.capabilities),
                    "supports_thinking": m.supports_thinking,
                    "supports_vision": m.supports_vision,
                }
                for m in self.list_all()
            ],
        }


# Singleton instance — constructed once at import, loaded at startup
registry = ModelRegistry()
