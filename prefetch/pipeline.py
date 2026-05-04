import asyncio
import logging
from dataclasses import dataclass, field

from memory.hybrid import compute_query_vectors, hybrid_search, rerank_by_recency, rerank_with_links
from memory.facts import get_client
from circuit_breaker import breakers
from prefetch.tools_retrieval import search_tools, build_tools_block, ToolMatch, CORE_TOOLS, FULL_SPEC_COUNT
from prefetch.cache import search_cache
from tools.tool_descriptions import TOOLS_SYSTEM_BLOCK

log = logging.getLogger(__name__)

TOKEN_WINDOW = 512
CHARS_PER_TOKEN = 4


@dataclass
class PrefetchContext:
    message: str
    history: list[dict]
    context_state: str
    session_id: str


@dataclass
class PrefetchResult:
    facts: list[dict] = field(default_factory=list)
    procedures: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)
    episodes: list[dict] = field(default_factory=list)
    tools_block: str = ""
    tool_names_full: set[str] = field(default_factory=set)

    @classmethod
    def fallback(cls) -> "PrefetchResult":
        return cls(tools_block=TOOLS_SYSTEM_BLOCK)


@dataclass
class _CollectionSpec:
    name: str
    top_k: int
    threshold: float
    use_links: bool = False


_MEMORY_COLLECTIONS = [
    _CollectionSpec("facts",      top_k=10, threshold=0.55),
    _CollectionSpec("procedures", top_k=8,  threshold=0.60),
    _CollectionSpec("sources",    top_k=5,  threshold=0.65, use_links=True),
    _CollectionSpec("notes",      top_k=5,  threshold=0.50, use_links=True),
    _CollectionSpec("episodes",   top_k=5,  threshold=0.50),
]


def _build_query(message: str, history: list[dict], context_state: str) -> str:
    char_budget = TOKEN_WINDOW * CHARS_PER_TOKEN
    parts = [message]
    remaining = char_budget - len(message)

    for turn in reversed(history[-20:]):
        if remaining <= 0:
            break
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        prefix_len = len(role) + 2  # "role: "
        available = remaining - prefix_len
        if available <= 0:
            break
        snippet = content[:available]
        parts.append(f"{role}: {snippet}")
        remaining -= len(snippet) + prefix_len

    parts.reverse()
    query = "\n".join(parts)
    if context_state:
        query = f"[mode:{context_state}] {query}"
    return query


async def _search_collection(
    spec: _CollectionSpec,
    dense_vec: list[float],
    sp_idx: list[int],
    sp_vals: list[float],
) -> list[dict]:
    cb = breakers["qdrant"]
    if not cb.can_execute():
        return []
    try:
        client = get_client()
        results = await hybrid_search(
            spec.name, dense_vec, sp_idx, sp_vals,
            spec.top_k, spec.threshold,
            client=client,
        )
        cb.record_success()
        if spec.use_links:
            return await rerank_with_links(spec.name, results, spec.top_k, client=client)
        return rerank_by_recency(results, spec.top_k)
    except Exception as e:
        cb.record_failure()
        log.warning("prefetch search_%s failed: %s", spec.name, e)
        return []


async def run_prefetch(ctx: PrefetchContext) -> PrefetchResult:
    try:
        query = _build_query(ctx.message, ctx.history, ctx.context_state)
        dense_vec, sp_idx, sp_vals = await compute_query_vectors(query)
    except Exception as e:
        log.warning("prefetch embed failed: %s — using fallback", e)
        return PrefetchResult.fallback()

    # Fan out: all memory collections + tools + cache in parallel
    memory_coros = [
        _search_collection(spec, dense_vec, sp_idx, sp_vals)
        for spec in _MEMORY_COLLECTIONS
    ]
    tools_coro = search_tools(
        dense_vec, sp_idx, sp_vals,
        ctx.context_state, ctx.session_id,
    )
    cache_coro = search_cache(dense_vec, sp_idx, sp_vals)

    results = await asyncio.gather(
        *memory_coros, tools_coro, cache_coro,
        return_exceptions=True,
    )

    # Unpack memory results (positions 0-4 match _MEMORY_COLLECTIONS order)
    memory_results = {}
    for i, spec in enumerate(_MEMORY_COLLECTIONS):
        r = results[i]
        memory_results[spec.name] = r if isinstance(r, list) else []

    # Unpack tools (position 5)
    tool_matches: list[ToolMatch] = results[5] if isinstance(results[5], list) else []

    # Build the dynamic tools block (falls back to static if no matches)
    if tool_matches:
        tools_block = build_tools_block(tool_matches)
    else:
        tools_block = TOOLS_SYSTEM_BLOCK

    tool_names_full = set(CORE_TOOLS)
    for m in tool_matches[:FULL_SPEC_COUNT]:
        tool_names_full.add(m.name)

    return PrefetchResult(
        facts=memory_results.get("facts", []),
        procedures=memory_results.get("procedures", []),
        sources=memory_results.get("sources", []),
        notes=memory_results.get("notes", []),
        episodes=memory_results.get("episodes", []),
        tools_block=tools_block,
        tool_names_full=tool_names_full,
    )
