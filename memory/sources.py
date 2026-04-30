import logging
from memory.facts import get_client, _rerank_by_recency, _hybrid_search
from circuit_breaker import breakers

log = logging.getLogger(__name__)


async def search_sources(query: str, top_k: int = 5, threshold: float = 0.65) -> list[dict]:
    cb = breakers["qdrant"]
    if not cb.can_execute():
        return []
    try:
        results = await _hybrid_search("sources", query, top_k, threshold)
        cb.record_success()
        return _rerank_by_recency(results, top_k)
    except Exception as e:
        cb.record_failure()
        log.warning("search_sources failed: %s", e)
        return []
