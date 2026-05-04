import logging
import time

from qdrant_client.models import (
    ScoredPoint, SparseVector, Prefetch, FusionQuery, Fusion, Filter,
    FieldCondition, MatchAny,
)

from tools.llm import embed
from memory.sparse import sparse_vector

log = logging.getLogger(__name__)

# Link boost weights by type — stronger signal = higher boost
LINK_TYPE_WEIGHTS: dict[str, float] = {
    "explicit_wikilink": 0.25,
    "curator_confirmed": 0.20,
    "concept_overlap": 0.15,
    "temporal_sequence": 0.10,
}
DEFAULT_LINK_WEIGHT = 0.15


async def compute_query_vectors(query: str) -> tuple[list[float], list[int], list[float]]:
    dense_vec = await embed(query)
    sp_idx, sp_vals = sparse_vector(query)
    return dense_vec, sp_idx, sp_vals


async def hybrid_search(
    collection: str,
    dense_vec: list[float],
    sp_idx: list[int],
    sp_vals: list[float],
    top_k: int,
    threshold: float,
    client=None,
    qdrant_filter: Filter | None = None,
) -> list[ScoredPoint]:
    if client is None:
        from memory.facts import get_client
        client = get_client()

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

    results = await client.query_points(
        collection_name=collection,
        prefetch=prefetch,
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k * 2,
        with_payload=True,
        query_filter=qdrant_filter,
    )
    return results.points


def rerank_by_recency(results: list[ScoredPoint], top_k: int) -> list[dict]:
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


def _collect_linked_ids(results: list[ScoredPoint]) -> dict[str, float]:
    """Extract linked point IDs from results with their best link weight."""
    linked: dict[str, float] = {}
    for r in results:
        for link in r.payload.get("links_to", []) + r.payload.get("linked_from", []):
            target = link.get("target", "")
            if not target:
                continue
            link_type = link.get("link_type", "")
            weight = LINK_TYPE_WEIGHTS.get(link_type, DEFAULT_LINK_WEIGHT)
            linked[target] = max(linked.get(target, 0), weight)
    return linked


async def rerank_with_links(
    collection: str,
    results: list[ScoredPoint],
    top_k: int,
    client=None,
) -> list[dict]:
    """Rerank by recency, then fetch and boost explicitly linked points.

    Points already in results that are also linked get a score boost.
    Linked points NOT in results are fetched and merged in with their link weight.
    """
    if client is None:
        from memory.facts import get_client
        client = get_client()

    now = time.time()
    seen_ids: set[str] = set()
    scored: list[tuple[float, dict]] = []

    # Score initial results with recency
    for r in results:
        rid = r.id if isinstance(r.id, str) else str(r.id)
        seen_ids.add(rid)
        ts = r.payload.get("timestamp", r.payload.get("ingested_at", 0))
        if isinstance(ts, str):
            ts = 0
        days = (now - ts) / 86400 if ts else 365
        recency = 1 / (1 + days * 0.05)
        scored.append((0.7 * r.score + 0.3 * recency, r.payload))

    # Collect linked IDs not already in results
    linked_weights = _collect_linked_ids(results)
    missing_ids = [pid for pid in linked_weights if pid not in seen_ids]

    if missing_ids:
        try:
            fetched = await client.retrieve(
                collection_name=collection,
                ids=missing_ids[:20],
                with_payload=True,
            )
            for point in fetched:
                pid = point.id if isinstance(point.id, str) else str(point.id)
                boost = linked_weights.get(pid, DEFAULT_LINK_WEIGHT)
                scored.append((boost, point.payload))
        except Exception as e:
            log.warning("link fetch from %s failed: %s", collection, e)

    # Boost results that are both semantically matched AND explicitly linked
    boosted = []
    for base_score, payload in scored:
        title = payload.get("title", "")
        text = payload.get("text", "")
        point_id = None
        for r in results:
            if r.payload is payload:
                point_id = r.id if isinstance(r.id, str) else str(r.id)
                break
        if point_id and point_id in linked_weights:
            base_score += linked_weights[point_id]
        boosted.append((base_score, payload))

    boosted.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in boosted[:top_k]]
