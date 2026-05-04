import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import ScoredPoint
from memory.hybrid import compute_query_vectors, hybrid_search, rerank_by_recency
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
        return rerank_by_recency(results, top_k)
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
        return rerank_by_recency(results, top_k)
    except Exception as e:
        cb.record_failure()
        log.warning("search_procedures failed: %s", e)
        return []


async def _hybrid_search(
    collection: str, query: str, top_k: int, threshold: float
) -> list[ScoredPoint]:
    dense_vec, sp_idx, sp_vals = await compute_query_vectors(query)
    return await hybrid_search(collection, dense_vec, sp_idx, sp_vals, top_k, threshold)


# Backward compat — other modules import these names from here
_rerank_by_recency = rerank_by_recency
