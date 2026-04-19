import asyncio
import json
import httpx
from datetime import datetime
from typing import AsyncGenerator

from memory.facts import search_facts
from memory.sources import search_sources
from memory.profile import get_profile
from memory.sessions import load_session, save_session
from router.classifier import RouteDecision
from tools.llm import chat_complete, curator_complete
from config import config

CODER_SYSTEM = """You are Coder, an expert programming and debugging assistant.
Date/time: {datetime}

User profile:
{profile}

Relevant facts:
{facts}

Relevant knowledge:
{sources}"""

TEACHER_SYSTEM = """You are Teacher, an expert at explaining complex topics clearly.
Date/time: {datetime}

User profile:
{profile}

Relevant facts:
{facts}

Relevant knowledge:
{sources}"""

CHAT_DUMP_SYSTEM = """You are an analytical assistant. Analyze the conversation content below.
Date/time: {datetime}"""


async def _split_code(content: str, language: str = "", filename: str = "") -> list[dict]:
    payload = {"code": content, "language": language or None, "filename": filename or None}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.code_splitter_url}/split/code", json=payload, timeout=30)
        r.raise_for_status()
        return r.json().get("chunks", [])


async def _split_logs(content: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.code_splitter_url}/split/logs", json={"text": content}, timeout=30)
        r.raise_for_status()
        return r.json().get("chunks", [])


async def _split_text(content: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.code_splitter_url}/split/text", json={"text": content}, timeout=30)
        r.raise_for_status()
        return r.json().get("chunks", [])


async def _split_chat_dump(content: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{config.code_splitter_url}/split/chat_dump", json={"text": content}, timeout=30)
        r.raise_for_status()
        return r.json().get("turns", [])


def _format_code_chunks(chunks: list[dict], filename: str = "") -> str:
    parts = []
    if filename:
        parts.append(f"# File: {filename}")
    for chunk in chunks:
        name = chunk.get("name", "")
        typ = chunk.get("type", "")
        lang = chunk.get("language", "")
        code = chunk.get("code", "")
        start = chunk.get("start_line")
        end = chunk.get("end_line")
        line_info = f" (lines {start}–{end})" if start else ""
        label = f"## {typ}: {name}{line_info}" if name else f"## {typ}{line_info}"
        parts.append(f"{label}\n```{lang}\n{code}\n```")
    return "\n\n".join(parts)


def _format_log_chunks(chunks: list[dict]) -> str:
    by_level: dict[str, list[str]] = {}
    for chunk in chunks:
        level = chunk.get("level", "UNKNOWN")
        by_level.setdefault(level, []).append(chunk.get("text", ""))

    parts = []
    for level in ["ERROR", "CRITICAL", "FATAL", "WARN", "WARNING", "INFO", "DEBUG", "UNKNOWN"]:
        if level in by_level:
            entries = by_level[level]
            parts.append(f"### {level} ({len(entries)} entries)\n" + "\n".join(entries[:20]))
    return "\n\n".join(parts)


async def _summarize_chunk(text: str) -> str:
    prompt = f"Summarize the following text concisely, preserving key facts:\n\n{text}"
    try:
        return await curator_complete([{"role": "user", "content": prompt}])
    except Exception:
        return text[:500]


async def _progressive_summarize(chunks: list[dict], text_field: str = "text") -> str:
    texts = [c.get(text_field, "") for c in chunks[:8] if c.get(text_field)]
    summaries = await asyncio.gather(*[_summarize_chunk(t) for t in texts])
    combined = "\n\n".join(summaries)
    if len(combined) > 5000:
        combined = await _summarize_chunk(combined)
    return combined


async def run_preprocessed(
    chat_input: str,
    files: list[dict] | None,
    chat_history: list[dict],
    session_id: str,
    route: RouteDecision,
) -> AsyncGenerator[str, None]:
    if not chat_history:
        chat_history = await load_session(session_id)

    profile = await get_profile()
    profile_text = json.dumps({k: v for k, v in profile.items() if k != "context_state"}, indent=2)
    retrieval_query = route.nl_prefix or chat_input

    # content to split: from file or inline text
    if files:
        first = files[0]
        raw_content = first.get("content", "")
        language = first.get("language", "")
        filename = first.get("name", "")
    else:
        raw_content = chat_input
        language = ""
        filename = ""

    # ── Split ────────────────────────────────────────────────────────────────
    system_tpl = CODER_SYSTEM

    if route.text_type == "code":
        chunks = await _split_code(raw_content, language, filename)
        formatted = _format_code_chunks(chunks, filename)

    elif route.text_type == "logs":
        chunks = await _split_logs(raw_content)
        formatted = _format_log_chunks(chunks)

    elif route.text_type == "chat_dump":
        turns = await _split_chat_dump(raw_content)
        formatted = "\n".join(
            f"{t.get('speaker', 'unknown')}: {t.get('text', '')}" for t in turns
        )
        system_tpl = CHAT_DUMP_SYSTEM

    else:  # document / unknown
        text_chunks = await _split_text(raw_content)
        system_tpl = TEACHER_SYSTEM
        if route.needs_summarization and len(text_chunks) > 2:
            formatted = await _progressive_summarize(text_chunks)
        else:
            formatted = "\n\n".join(c.get("text", "") for c in text_chunks)

    # ── Retrieval ────────────────────────────────────────────────────────────
    if route.use_retrieval and retrieval_query.strip():
        facts_list, sources_list = await asyncio.gather(
            search_facts(retrieval_query, top_k=5),
            search_sources(retrieval_query, top_k=5),
        )
    else:
        facts_list, sources_list = [], []

    facts_text = "\n".join(f"- {f.get('text', '')}" for f in facts_list) or "None"
    sources_text = "\n".join(f"- {s.get('text', s.get('content', ''))[:300]}" for s in sources_list) or "None"

    # ── System prompt ─────────────────────────────────────────────────────────
    fmt_kwargs: dict = {"datetime": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if system_tpl != CHAT_DUMP_SYSTEM:
        fmt_kwargs.update(profile=profile_text, facts=facts_text, sources=sources_text)
    system = system_tpl.format(**fmt_kwargs)

    # ── Messages ──────────────────────────────────────────────────────────────
    messages = [{"role": "system", "content": system}]
    for turn in chat_history[-20:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # user message: split content block + question (if file-based)
    user_parts = []
    if formatted:
        user_parts.append(formatted)
    if files and chat_input.strip():
        user_parts.append(chat_input)
    messages.append({"role": "user", "content": "\n\n".join(user_parts)})

    # ── Stream ────────────────────────────────────────────────────────────────
    response_text = ""
    thinking_text = ""

    async for chunk in await chat_complete(messages, stream=True):
        choice = chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})

        if delta.get("reasoning_content"):
            thinking_text += delta["reasoning_content"]
            yield json.dumps({"type": "thinking", "text": delta["reasoning_content"]})

        if delta.get("content"):
            response_text += delta["content"]
            yield json.dumps({"type": "text", "text": delta["content"]})

    # ── Save session (original chat_input as user turn) ───────────────────────
    saved_user = chat_input if chat_input.strip() else f"[{filename or route.text_type}]"
    new_history = chat_history + [
        {"role": "user", "content": saved_user},
        {"role": "assistant", "content": response_text, "thoughts": thinking_text},
    ]
    await save_session(session_id, new_history)
