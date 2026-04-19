from memory.facts import get_client, _rerank_by_recency
from tools.llm import embed


async def search_sources(query: str, top_k: int = 5, threshold: float = 0.65) -> list[dict]:
    vector = await embed(query)
    results = await get_client().query_points(
        collection_name="sources",
        query=vector,
        limit=top_k * 2,
        score_threshold=threshold,
        with_payload=True,
    )
    return _rerank_by_recency(results.points, top_k)
