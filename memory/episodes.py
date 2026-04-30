import logging
import time
import uuid
from qdrant_client.models import PointStruct, SparseVector
from memory.facts import get_client, _rerank_by_recency, _hybrid_search
from memory.sparse import sparse_vector
from tools.llm import embed, curator_complete
from circuit_breaker import breakers

log = logging.getLogger(__name__)

TOKEN_COMPRESS_THRESHOLD = 24_000  # estimated tokens before compression triggers
TOKEN_KEEP_TARGET = 8_000         # target tokens to keep after compression
MIN_TURNS_KEEP = 6                # never compress below this many turns


def _estimate_tokens(history: list[dict]) -> int:
    """Rough token estimate: chars / 4."""
    total = 0
    for turn in history:
        content = turn.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total += len(block.get("text", ""))
    return total // 4


def _find_keep_index(history: list[dict]) -> int:
    """Walk backwards from end, accumulating tokens until we hit the keep target."""
    total = 0
    for i in range(len(history) - 1, -1, -1):
        content = history[i].get("content", "")
        if isinstance(content, str):
            total += len(content) // 4
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total += len(block.get("text", "")) // 4
        if total >= TOKEN_KEEP_TARGET:
            return i
    return 0

SUMMARY_PROMPT = """Summarize the following conversation exchange into a concise episode memory.
Capture: main topics discussed, decisions made, key facts learned, and outcomes.
Be factual and specific. Write 2-5 sentences.

{turns}

Summary:"""


async def maybe_compress(session_id: str, history: list[dict]) -> list[dict]:
    """If history exceeds token threshold, compress old turns into episodes and return trimmed history."""
    tokens = _estimate_tokens(history)
    if tokens <= TOKEN_COMPRESS_THRESHOLD:
        return history

    keep_idx = _find_keep_index(history)
    keep_idx = min(keep_idx, len(history) - MIN_TURNS_KEEP)
    if keep_idx <= 0:
        return history

    old_turns = history[:keep_idx]
    recent_turns = history[keep_idx:]
    log.info("compressing: %d tokens, keeping %d/%d turns (~%d tokens)",
             tokens, len(recent_turns), len(history), _estimate_tokens(recent_turns))

    # Format old turns for summarization
    lines = []
    for turn in old_turns:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            lines.append(f"{role.upper()}: {content[:500]}")

    if not lines:
        return recent_turns

    turns_text = "\n".join(lines)
    prompt = SUMMARY_PROMPT.format(turns=turns_text)

    try:
        summary = await curator_complete([{"role": "user", "content": prompt}])
        summary = summary.strip()
    except Exception:
        return recent_turns

    # Store episode in Qdrant
    cb = breakers["qdrant"]
    if not cb.can_execute():
        log.warning("Qdrant circuit open — skipping episode storage")
        return recent_turns
    try:
        dense_vec = await embed(summary)
        sp_idx, sp_vals = sparse_vector(summary)
        vectors = {"dense": dense_vec}
        if sp_idx:
            vectors["sparse"] = SparseVector(indices=sp_idx, values=sp_vals)
        point_id = str(uuid.uuid4())
        await get_client().upsert(
            collection_name="episodes",
            points=[PointStruct(
                id=point_id,
                vector=vectors,
                payload={
                    "text": summary,
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "turn_count": len(old_turns),
                    "source": "compression",
                },
            )],
        )
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        log.warning("Episode storage failed: %s", e)

    return recent_turns


async def search_episodes(query: str, top_k: int = 5, threshold: float = 0.5) -> list[dict]:
    cb = breakers["qdrant"]
    if not cb.can_execute():
        return []
    try:
        results = await _hybrid_search("episodes", query, top_k, threshold)
        cb.record_success()
        return _rerank_by_recency(results, top_k)
    except Exception as e:
        cb.record_failure()
        log.warning("search_episodes failed: %s", e)
        return []
