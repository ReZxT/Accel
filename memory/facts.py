import time
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, ScoredPoint
from tools.llm import embed
from config import config

_client: AsyncQdrantClient | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=config.qdrant_url)
    return _client


async def search_facts(query: str, top_k: int = 10, threshold: float = 0.55) -> list[dict]:
    vector = await embed(query)
    results = await get_client().query_points(
        collection_name="facts",
        query=vector,
        limit=top_k * 2,
        score_threshold=threshold,
        with_payload=True,
    )
    return _rerank_by_recency(results.points, top_k)


async def search_procedures(query: str, top_k: int = 8, threshold: float = 0.6) -> list[dict]:
    vector = await embed(query)
    results = await get_client().query_points(
        collection_name="procedures",
        query=vector,
        limit=top_k * 2,
        score_threshold=threshold,
        with_payload=True,
    )
    return _rerank_by_recency(results.points, top_k)


def _rerank_by_recency(results: list[ScoredPoint], top_k: int) -> list[dict]:
    now = time.time()
    scored = []
    for r in results:
        ts = r.payload.get("timestamp", 0)
        days = (now - ts) / 86400 if ts else 365
        recency = 1 / (1 + days * 0.05)
        combined = 0.7 * r.score + 0.3 * recency
        scored.append((combined, r.payload))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_k]]
