import logging
import time
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, ScoredPoint,
    SparseVector, Prefetch, FusionQuery, Fusion,
)
from tools.llm import embed
from memory.sparse import sparse_vector
from config import config
from circuit_breaker import breakers

log = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=config.qdrant_url)
    return _client


async def search_facts(query: str, top_k: int = 10, threshold: float = 0.55) -> list[dict]:
    cb = breakers["qdrant"]
    if not cb.can_execute():
        log.warning("Qdrant circuit open — skipping fact retrieval")
        return []
    try:
        results = await _hybrid_search("facts", query, top_k, threshold)
        cb.record_success()
        return _rerank_by_recency(results, top_k)
    except Exception as e:
        cb.record_failure()
        log.warning("search_facts failed: %s", e)
        return []


async def search_procedures(query: str, top_k: int = 8, threshold: float = 0.6) -> list[dict]:
    cb = breakers["qdrant"]
    if not cb.can_execute():
        return []
    try:
        results = await _hybrid_search("procedures", query, top_k, threshold)
        cb.record_success()
        return _rerank_by_recency(results, top_k)
    except Exception as e:
        cb.record_failure()
        log.warning("search_procedures failed: %s", e)
        return []


async def _hybrid_search(
    collection: str, query: str, top_k: int, threshold: float
) -> list[ScoredPoint]:
    """Run dense + sparse hybrid search with RRF fusion."""
    dense_vec = await embed(query)
    sp_idx, sp_vals = sparse_vector(query)

    prefetch = [
        Prefetch(
            query=dense_vec,
            using="dense",
            limit=top_k * 3,
            score_threshold=threshold,
        ),
    ]
    if sp_idx:
        prefetch.append(Prefetch(
            query=SparseVector(indices=sp_idx, values=sp_vals),
            using="sparse",
            limit=top_k * 3,
        ))

    results = await get_client().query_points(
        collection_name=collection,
        prefetch=prefetch,
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k * 2,
        with_payload=True,
    )
    return results.points


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
