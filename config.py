import os
from dataclasses import dataclass


@dataclass
class Config:
    # Inference endpoints
    chat_url: str = os.getenv("CHAT_URL", "http://localhost:8080/v1")
    curator_url: str = os.getenv("CURATOR_URL", "http://localhost:8082/v1")
    embed_url: str = os.getenv("EMBED_URL", "http://localhost:8081/v1")

    # Model names (as llama.cpp reports them)
    chat_model: str = os.getenv("CHAT_MODEL", "accel")
    curator_model: str = os.getenv("CURATOR_MODEL", "curator")
    embed_model: str = os.getenv("EMBED_MODEL", "embed")

    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")

    # Supporting services
    code_splitter_url: str = os.getenv("CODE_SPLITTER_URL", "http://localhost:9200")
    minio_url: str = os.getenv("MINIO_URL", "http://localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    # API server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8100"))

    # Inference settings
    context_window: int = int(os.getenv("CONTEXT_WINDOW", "65536"))
    default_thinking_budget: int = int(os.getenv("THINKING_BUDGET", "2048"))


config = Config()
