import logging
import re
from dataclasses import dataclass, field

from memory.hybrid import hybrid_search
from memory.facts import get_client
from circuit_breaker import breakers
from prefetch.tool_stats import tool_stats
from tools.tool_descriptions import TOOL_DETAILS, TOOLS_SYSTEM_BLOCK

log = logging.getLogger(__name__)

CORE_TOOLS = frozenset({"get_tool_description", "search_collection"})
FULL_SPEC_COUNT = 7
BRIEF_COUNT = 13  # positions 8-20

TOOL_CATEGORIES: dict[str, str] = {
    "read_file": "file", "write_file": "file", "edit_file": "file",
    "delete_file": "file", "get_file_info": "file", "move_file": "file",
    "bash": "system", "search_files": "system", "list_dir": "system",
    "search_web": "web", "fetch_url": "web", "screenshot_url": "web", "download_file": "web",
    "calculate": "compute", "convert_units": "compute", "convert_currency": "compute",
    "calendar_today": "calendar", "calendar_get_events": "calendar",
    "calendar_add_event": "calendar", "calendar_delete_event": "calendar",
    "list_collections": "memory", "search_collection": "memory",
    "save_memory": "memory", "update_memory": "memory", "delete_memory": "memory",
    "search_facts": "memory", "search_procedures": "memory", "search_episodes": "memory",
    "search_notes": "memory", "list_notes": "memory",
    "search_knowledge_base": "memory", "list_knowledge_base": "memory",
    "ingest_file": "memory", "ingest_note": "memory",
    "delete_source": "memory", "delete_note": "memory",
    "search_music": "music", "download_music": "music",
    "navidrome_search": "music", "navidrome_get_playlists": "music",
    "navidrome_get_playlist": "music", "navidrome_create_playlist": "music",
    "navidrome_update_playlist": "music", "navidrome_delete_playlist": "music",
    "player_control": "music", "player_now_playing": "music", "player_load": "music",
    "soundcloud_get_playlists": "music", "soundcloud_get_playlist": "music",
    "search_audiobooks": "media", "add_torrent": "media",
    "canvas_draw": "canvas", "canvas_clear": "canvas",
    "canvas_get_state": "canvas", "canvas_screenshot": "canvas",
    "career_get_profile": "career", "career_update_profile": "career",
    "career_save_offer": "career", "career_list_offers": "career",
    "career_get_offer": "career", "career_rate_offer": "career",
    "career_delete_offer": "career", "career_tierlist": "career",
    "career_compare": "career", "career_fetch_jobs": "career",
    "get_tool_description": "system",
}

TOOL_MODES: dict[str, list[str]] = {
    "canvas_draw": ["architecture"],
    "canvas_clear": ["architecture"],
    "canvas_get_state": ["architecture"],
    "canvas_screenshot": ["architecture"],
    "player_control": ["music", "free"],
    "player_now_playing": ["music", "free"],
    "player_load": ["music", "free"],
    "navidrome_search": ["music", "free"],
    "navidrome_get_playlists": ["music"],
    "navidrome_get_playlist": ["music"],
    "navidrome_create_playlist": ["music"],
    "navidrome_update_playlist": ["music"],
    "navidrome_delete_playlist": ["music"],
    "soundcloud_get_playlists": ["music"],
    "soundcloud_get_playlist": ["music"],
    "search_music": ["music", "free"],
    "download_music": ["music", "free"],
    "career_get_profile": ["work"],
    "career_update_profile": ["work"],
    "career_save_offer": ["work"],
    "career_list_offers": ["work"],
    "career_get_offer": ["work"],
    "career_rate_offer": ["work"],
    "career_delete_offer": ["work"],
    "career_tierlist": ["work"],
    "career_compare": ["work"],
    "career_fetch_jobs": ["work"],
}

# Extract the XML protocol header from TOOLS_SYSTEM_BLOCK (everything up to "Available tools:")
_header_end = TOOLS_SYSTEM_BLOCK.find("Available tools:")
TOOLS_PROTOCOL_HEADER = TOOLS_SYSTEM_BLOCK[:_header_end] if _header_end > 0 else ""


@dataclass
class ToolMatch:
    name: str
    score: float
    final_score: float = 0.0
    one_liner: str = ""
    full_spec: str = ""
    category: str = ""
    irreversible: bool = False
    modes: list[str] = field(default_factory=list)


def _extract_one_liner(name: str) -> str:
    pattern = rf"^{re.escape(name)} — (.+)$"
    m = re.search(pattern, TOOLS_SYSTEM_BLOCK, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _compute_final_score(
    match: ToolMatch, context_state: str, session_id: str
) -> float:
    base = match.score
    recency = tool_stats.get_recency_score(match.name) * 0.15
    mode_boost = 0.0
    if match.modes:
        if context_state in match.modes:
            mode_boost = 0.15
        else:
            mode_boost = -0.05
    cooc = tool_stats.get_cooccurrence_boost(match.name, session_id) * 0.10
    return base + recency + mode_boost + cooc


async def search_tools(
    dense_vec: list[float],
    sp_idx: list[int],
    sp_vals: list[float],
    context_state: str,
    session_id: str,
    top_k: int = 25,
    threshold: float = 0.35,
) -> list[ToolMatch]:
    cb = breakers["tools_qdrant"]
    if not cb.can_execute():
        return []
    try:
        results = await hybrid_search(
            "tools", dense_vec, sp_idx, sp_vals, top_k, threshold,
            client=get_client(),
        )
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        log.warning("search_tools failed: %s", e)
        return []

    matches = []
    for r in results:
        p = r.payload
        match = ToolMatch(
            name=p.get("name", ""),
            score=r.score,
            one_liner=p.get("one_liner", ""),
            full_spec=p.get("full_spec", ""),
            category=p.get("category", ""),
            irreversible=p.get("irreversible", False),
            modes=p.get("modes", []),
        )
        match.final_score = _compute_final_score(match, context_state, session_id)
        matches.append(match)

    matches.sort(key=lambda m: m.final_score, reverse=True)
    return matches


def build_tools_block(matches: list[ToolMatch]) -> str:
    seen = set()
    full_specs: list[str] = []
    brief_lines: list[str] = []

    # Core tools always get full spec
    for name in sorted(CORE_TOOLS):
        spec = TOOL_DETAILS.get(name, "")
        if spec:
            full_specs.append(spec)
            seen.add(name)

    # Top N matches get full spec
    full_count = 0
    brief_count = 0
    for m in matches:
        if m.name in seen:
            continue
        if full_count < FULL_SPEC_COUNT:
            spec = m.full_spec or TOOL_DETAILS.get(m.name, "")
            if not spec:
                continue
            full_specs.append(spec)
            seen.add(m.name)
            full_count += 1
        elif brief_count < BRIEF_COUNT:
            liner = m.one_liner or _extract_one_liner(m.name)
            if not liner:
                continue
            brief_lines.append(f"{m.name} — {liner}")
            seen.add(m.name)
            brief_count += 1
        else:
            break

    parts = [TOOLS_PROTOCOL_HEADER.rstrip()]
    parts.append("\nAvailable tools (full specs — use directly):\n")
    parts.append("\n\n".join(full_specs))
    if brief_lines:
        parts.append("\n\nOther available tools (call get_tool_description for full spec):\n")
        parts.append("\n".join(brief_lines))
    parts.append("\n\nAfter each tool call you will receive a <tool_result> block. Use it to inform your next step.")
    parts.append("\nDo not emit multiple tool calls at once unless they are fully independent.")
    parts.append("\nNEVER paste raw URLs as your answer — always use fetch_url or search_web to retrieve content, then summarize the results.")

    return "\n".join(parts)
