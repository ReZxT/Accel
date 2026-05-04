import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
import httpx
from datetime import datetime
from typing import AsyncGenerator

log = logging.getLogger(__name__)

from memory.profile import get_profile, get_tool_settings
from memory.sessions import load_session, save_session
from memory.extraction import extract_after_response
from memory.episodes import maybe_compress
from router.classifier import RouteDecision
from router.tier0 import Tier0Result
from tools.llm import chat_complete
from tools.tool_parser import parse_xml_tool_calls, strip_tool_calls
from tools.tool_descriptions import TOOLS_SYSTEM_BLOCK
from tools.code_tools import execute_tool, IRREVERSIBLE_TOOLS
from tools import approval
from config import config
from models.registry import registry
from prefetch.pipeline import run_prefetch, PrefetchContext
from prefetch.tool_stats import tool_stats

MAX_TOOL_ITERATIONS = 25
TOOL_CONTINUE_BATCH = 25
STALL_WINDOW = 3  # consecutive duplicate rounds before stall is declared


def _fingerprint_calls(tool_calls: list[dict]) -> str:
    """Hash the tool names + args for this round to detect repeated call patterns."""
    parts = []
    for tc in sorted(tool_calls, key=lambda t: t["name"]):
        parts.append(f"{tc['name']}:{json.dumps(tc['args'], sort_keys=True)}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _fingerprint_text(text: str) -> str:
    """Hash response text (normalized) to detect repeated outputs."""
    return hashlib.md5(text.strip().encode()).hexdigest()


def _assistant_content(text: str, thinking: str) -> str:
    if thinking:
        return f"<think>{thinking}</think>\n{text}" if text else f"<think>{thinking}</think>"
    return text

SYSTEM_TEMPLATE = """You are {personality}, an AI assistant.
Date/time: {datetime}
Context: {context_state}

User profile:
{profile}

Relevant facts:
{facts}

Relevant procedures:
{procedures}

Relevant notes (auto-retrieved from Obsidian vault):
{notes}
Note: use search_notes to retrieve more vault notes on demand, list_notes to see all indexed notes, edit_file + ingest_note to update a note and re-index it.

Relevant knowledge (auto-retrieved from books and documents):
{sources}
Note: use search_knowledge_base to retrieve more from the knowledge base on demand, list_knowledge_base to see what is ingested.
{tools_block}"""


async def _store_image(img: dict, session_id: str, index: int) -> None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"{config.code_splitter_url}/store/image",
                json={
                    "base64": img["base64"],
                    "mime_type": img.get("type", "image/png"),
                    "session_id": session_id,
                    "index": index,
                },
            )
    except Exception:
        pass


async def _preprocess_images(images: list[dict], session_id: str) -> list[dict]:
    asyncio.gather(*[_store_image(img, session_id, i) for i, img in enumerate(images)])
    processed = []
    async with httpx.AsyncClient(timeout=30) as client:
        for img in images:
            try:
                r = await client.post(
                    f"{config.code_splitter_url}/preprocess/image",
                    json={"base64": img["base64"], "mime_type": img.get("type", "image/png")},
                )
                r.raise_for_status()
                result = r.json()
                processed.append({"base64": result["base64"], "mime_type": result["mime_type"]})
            except Exception:
                processed.append({"base64": img["base64"], "mime_type": img.get("type", "image/png")})
    return processed


async def _needs_approval(tool_name: str, tool_settings: dict) -> bool:
    policy = tool_settings.get(tool_name, "require" if tool_name in IRREVERSIBLE_TOOLS else "auto")
    return policy == "require"


async def _run_agentic_loop(
    messages: list[dict],
    budget_kwargs: dict,
    session_id: str,
    tool_settings: dict,
    cancel: asyncio.Event | None = None,
    model_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Streaming agentic loop: call model, parse tool calls, execute, repeat."""
    nudged = False
    stall_nudged = False
    iterations = 0
    loop_t0 = time.monotonic()
    recent_call_fps: list[str] = []
    recent_text_fps: list[str] = []
    while True:
        if cancel and cancel.is_set():
            yield json.dumps({"type": "text", "text": "\n\n*(Cancelled.)*"})
            break

        response_text = ""
        thinking_text = ""

        # stream model response token-by-token
        async for chunk in await chat_complete(messages, stream=True, model_id=model_id, **budget_kwargs):
            if cancel and cancel.is_set():
                break
            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            if delta.get("reasoning_content"):
                thinking_text += delta["reasoning_content"]
                yield json.dumps({"type": "thinking", "text": delta["reasoning_content"]})
            if delta.get("content"):
                response_text += delta["content"]
                yield json.dumps({"type": "text_delta", "text": delta["content"]})

        if cancel and cancel.is_set():
            yield json.dumps({"type": "text", "text": "\n\n*(Cancelled.)*"})
            messages.append({"role": "assistant", "content": response_text or "(cancelled)"})
            break

        # extract <think> blocks from content field (DIMOE / DeepSeek V4)
        think_blocks = re.findall(r"<think>([\s\S]*?)</think>", response_text, re.IGNORECASE)
        # DeepSeek V4 non-think mode: leading </think> → strip it
        response_text = re.sub(r"^\s*</think>\s*", "", response_text, flags=re.IGNORECASE)
        if think_blocks:
            extra_thinking = "\n".join(think_blocks).strip()
            response_text = re.sub(r"<think>[\s\S]*?</think>", "", response_text, flags=re.IGNORECASE).strip()
        else:
            extra_thinking = ""

        tool_calls = parse_xml_tool_calls(response_text)
        clean_text = strip_tool_calls(response_text) if tool_calls else response_text

        if not clean_text and not tool_calls and extra_thinking:
            thinking_text += extra_thinking
            yield json.dumps({"type": "text", "text": extra_thinking})
        else:
            if extra_thinking:
                thinking_text += extra_thinking
                yield json.dumps({"type": "thinking", "text": extra_thinking})
            if tool_calls and clean_text:
                # Tool round: streamed tokens included XML — send cleaned version
                yield json.dumps({"type": "text_replace", "text": clean_text})

        if not tool_calls:
            # model produced no text and no tool calls — nudge once then stop
            if not clean_text and not extra_thinking and not nudged:
                nudged = True
                messages.append({"role": "assistant", "content": ""})
                messages.append({"role": "user", "content": "Please provide your response."})
                continue
            # Append final response to messages so run_chat can save the full exchange
            messages.append({"role": "assistant", "content": _assistant_content(response_text, thinking_text)})
            break

        iterations += 1

        # -- stall detection --
        call_fp = _fingerprint_calls(tool_calls)
        text_fp = _fingerprint_text(response_text)
        recent_call_fps.append(call_fp)
        recent_text_fps.append(text_fp)
        if len(recent_call_fps) > STALL_WINDOW:
            recent_call_fps.pop(0)
            recent_text_fps.pop(0)

        calls_repeating = len(recent_call_fps) == STALL_WINDOW and len(set(recent_call_fps)) == 1
        text_repeating = len(recent_text_fps) == STALL_WINDOW and len(set(recent_text_fps)) == 1

        if calls_repeating or text_repeating:
            if stall_nudged:
                log.warning("stall: force-stopping after nudge failed  session=%s  iterations=%d", session_id, iterations)
                yield json.dumps({"type": "text", "text": "\n\n*(Stopped — repeated actions with no progress.)*"})
                messages.append({"role": "assistant", "content": _assistant_content(response_text, thinking_text)})
                break
            stall_nudged = True
            log.warning("stall: detected repeated pattern  session=%s  iterations=%d", session_id, iterations)
            messages.append({"role": "assistant", "content": _assistant_content(response_text, thinking_text)})
            messages.append({"role": "user", "content": "You are repeating the same actions. Stop using tools and provide your best answer with the information you already have."})
            recent_call_fps.clear()
            recent_text_fps.clear()
            continue

        if iterations >= MAX_TOOL_ITERATIONS:
            request_id = str(uuid.uuid4())
            approval.register(request_id)
            yield json.dumps({
                "type": "approval_request",
                "request_id": request_id,
                "tool": "__continue__",
                "args": {"iterations_used": iterations, "message": f"Reached {iterations} tool calls. Continue for another {TOOL_CONTINUE_BATCH}?"},
            })
            approved = await approval.wait_for_approval(request_id)
            if not approved:
                yield json.dumps({"type": "text", "text": f"\n\n*(Stopped after {iterations} tool iterations.)*"})
                break
            iterations = 0

        # emit separator before tool activity
        yield json.dumps({"type": "tool_start"})

        # Include thinking in intermediate assistant messages too
        messages.append({"role": "assistant", "content": _assistant_content(response_text, thinking_text)})

        tool_result_parts = []
        for tc in tool_calls:
            if cancel and cancel.is_set():
                break
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            # approval gate
            if await _needs_approval(tool_name, tool_settings):
                request_id = str(uuid.uuid4())
                approval.register(request_id)
                yield json.dumps({
                    "type": "approval_request",
                    "request_id": request_id,
                    "tool": tool_name,
                    "args": tool_args,
                })
                approved = await approval.wait_for_approval(request_id)
                if not approved:
                    result = f"[Tool '{tool_name}' was denied by user]"
                    yield json.dumps({"type": "tool_denied", "tool": tool_name})
                    tool_result_parts.append(
                        f"<tool_result>\n<function={tool_name}>\n{result}\n</function>\n</tool_result>"
                    )
                    continue

            # emit tool_call event (shown in UI)
            yield json.dumps({"type": "tool_call", "tool": tool_name, "args": tool_args})
            log.info("tool_call: %s  args=%s  session=%s", tool_name, json.dumps(tool_args)[:200], session_id)

            tool_t0 = time.monotonic()
            tool_task = asyncio.ensure_future(execute_tool(tool_name, tool_args, session_id))
            while True:
                done, _ = await asyncio.wait({tool_task}, timeout=15)
                if done:
                    break
                if cancel and cancel.is_set():
                    tool_task.cancel()
                    yield json.dumps({"type": "text", "text": "\n\n*(Cancelled.)*"})
                    return
                yield json.dumps({"type": "heartbeat"})
            result = tool_task.result()
            log.info("tool_done: %s  %.1fs  session=%s", tool_name, time.monotonic() - tool_t0, session_id)

            # image result (e.g. screenshot_url)
            if isinstance(result, dict) and result.get("__type") == "image":
                b64 = result["base64"]
                mime = result.get("mime_type", "image/png")
                url = result.get("url", "")
                yield json.dumps({"type": "tool_result", "tool": tool_name, "output": f"[Screenshot of {url}]", "image": b64, "mime_type": mime})
                tool_result_parts.append({
                    "__type": "image",
                    "tool": tool_name,
                    "base64": b64,
                    "mime_type": mime,
                    "url": url,
                })
            elif isinstance(result, dict) and result.get("__type") == "canvas_command":
                yield json.dumps({"type": "canvas_command", "command": result.get("command"), "data": result.get("data")})
                summary = result.get("summary", "Canvas updated.")
                yield json.dumps({"type": "tool_result", "tool": tool_name, "output": summary})
                tool_result_parts.append(
                    f"<tool_result>\n<function={tool_name}>\n{summary}\n</function>\n</tool_result>"
                )
            elif isinstance(result, dict) and result.get("__type") == "open_panel":
                mode = result.get("mode", "file")
                payload = result.get("payload", {})
                summary = result.get("summary", f"Opening {mode} panel.")
                yield json.dumps({"type": "open_panel", "mode": mode, "payload": payload})
                yield json.dumps({"type": "tool_result", "tool": tool_name, "output": summary})
                tool_result_parts.append(
                    f"<tool_result>\n<function={tool_name}>\n{summary}\n</function>\n</tool_result>"
                )
            elif isinstance(result, dict) and result.get("__type") == "play_queue":
                tracks = result.get("tracks", [])
                summary = f"Loading {len(tracks)} track(s) into player: " + ", ".join(t.get("title", "?") for t in tracks[:3])
                yield json.dumps({"type": "play_queue", "tracks": tracks})
                yield json.dumps({"type": "tool_result", "tool": tool_name, "output": summary})
                tool_result_parts.append(
                    f"<tool_result>\n<function={tool_name}>\n{summary}\n</function>\n</tool_result>"
                )
            elif isinstance(result, dict) and result.get("__type") == "error":
                text = result.get("text", "Tool error")
                yield json.dumps({"type": "tool_result", "tool": tool_name, "output": text})
                tool_result_parts.append(
                    f"<tool_result>\n<function={tool_name}>\n{text}\n</function>\n</tool_result>"
                )
            else:
                yield json.dumps({"type": "tool_result", "tool": tool_name, "output": result})
                tool_result_parts.append(
                    f"<tool_result>\n<function={tool_name}>\n{result}\n</function>\n</tool_result>"
                )

        # build tool result message — mix text and images
        text_parts = [p for p in tool_result_parts if isinstance(p, str)]
        image_parts = [p for p in tool_result_parts if isinstance(p, dict)]

        if image_parts:
            content_blocks = []
            if text_parts:
                content_blocks.append({"type": "text", "text": "\n".join(text_parts)})
            for img in image_parts:
                content_blocks.append({"type": "text", "text": f"<tool_result>\n<function={img['tool']}>\n[Screenshot of {img['url']}]\n</function>\n</tool_result>"})
                content_blocks.append({"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64']}"}})
            messages.append({"role": "user", "content": content_blocks})
        else:
            messages.append({"role": "user", "content": "\n".join(text_parts)})

    return


async def run_chat(
    chat_input: str,
    chat_history: list[dict],
    session_id: str,
    images: list[dict] | None = None,
    route: RouteDecision | None = None,
    voice_mode: bool = False,
    cancel: asyncio.Event | None = None,
    tier0: Tier0Result | None = None,
    model_id: str | None = None,
    thinking_enabled: bool | None = None,
) -> AsyncGenerator[str, None]:
    req_t0 = time.monotonic()
    log.info("run_chat: session=%s  voice=%s  tier0=%s  model=%s  input=%.80s",
             session_id, voice_mode, tier0.intent if tier0 else None,
             model_id or "default", chat_input)

    if not chat_history:
        chat_history = await load_session(session_id)

    chat_history = await maybe_compress(session_id, chat_history)

    profile = await get_profile()
    context_state = profile.get("context_state", "free")
    tool_settings = await get_tool_settings()

    personality = tier0.force_personality if (tier0 and tier0.force_personality) else "Casual"

    # Pre-fetch: single embed → fan out to all collections in parallel
    skip = tier0 is not None and tier0.skip_retrieval
    if skip:
        from prefetch.pipeline import PrefetchResult
        ctx = PrefetchResult.fallback()
    else:
        ctx = await run_prefetch(PrefetchContext(
            message=chat_input,
            history=chat_history,
            context_state=context_state,
            session_id=session_id,
        ))

    facts_text = "\n".join(f"- {f.get('text', '')}" for f in ctx.facts) or "None"
    proc_text = "\n".join(f"- {p.get('text', '')}" for p in ctx.procedures) or "None"

    def _fmt_source(s: dict) -> str:
        title = s.get("title", "")
        filepath = s.get("filepath", "")
        text = s.get("text", s.get("content", ""))[:300]
        label = f"[{title} — {filepath}]" if filepath else (f"[{title}]" if title else "")
        return f"{label} {text}".strip()

    sources_text = "\n".join(f"- {_fmt_source(s)}" for s in ctx.sources) or "None"
    notes_text = "\n".join(f"- {_fmt_source(n)}" for n in ctx.notes) or "None"
    profile_text = json.dumps(
        {k: v for k, v in profile.items() if k not in ("context_state", "tool_settings")},
        indent=2,
    )

    system = SYSTEM_TEMPLATE.format(
        personality=personality,
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
        context_state=context_state,
        profile=profile_text,
        facts=facts_text,
        procedures=proc_text,
        notes=notes_text,
        sources=sources_text,
        tools_block=ctx.tools_block,
    )
    if voice_mode:
        system += "\n\n[VOICE MODE] Respond in 1-3 concise spoken sentences unless the user explicitly asks to explain or expand. No markdown, no bullet points, no code blocks. Natural spoken language only."

    messages = [{"role": "system", "content": system}]
    for turn in chat_history[-40:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role not in ("user", "assistant") or not content:
            continue
        messages.append({"role": role, "content": content})

    if images:
        processed = await _preprocess_images(images, session_id)
        user_content = [{"type": "text", "text": chat_input}]
        for img in processed:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64']}"},
            })
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": chat_input})

    loop_start = len(messages)  # index of first new turn added by the loop

    # Determine active model for this response — used for thinking config + UI info
    active_model = registry.get(model_id) if model_id else registry.chat
    budget_kwargs: dict = {}
    # Respect explicit thinking_enabled flag; otherwise use model default
    use_thinking = thinking_enabled if thinking_enabled is not None else (active_model and active_model.supports_thinking)
    if active_model and use_thinking:
        if active_model.provider == "llama_cpp":
            budget_kwargs = {"extra_body": {"thinking_budget_tokens": 16384}}
        elif "deepseek" in active_model.id:
            # DeepSeek V4: native thinking toggle + effort level
            budget_kwargs = {
                "thinking": {"type": "enabled"},
                "reasoning_effort": "high",
            }
    elif active_model and "deepseek" in active_model.id and thinking_enabled is False:
        # Explicitly disable thinking for DeepSeek
        budget_kwargs = {"thinking": {"type": "disabled"}}

    # Tell the UI which model is active for this response
    if active_model:
        yield json.dumps({"type": "model_info", "model_id": active_model.id, "model_name": active_model.name, "provider": active_model.provider})

    # agentic loop — accumulate final response text for extraction/display
    response_text = ""
    thinking_text = ""
    tool_log: list[dict] = []
    _current_tool: str | None = None

    async for event_json in _run_agentic_loop(messages, budget_kwargs, session_id, tool_settings, cancel=cancel, model_id=model_id):
        event = json.loads(event_json)
        etype = event["type"]
        if etype in ("text", "text_delta", "text_replace"):
            if etype == "text_replace":
                response_text = event["text"]
            else:
                response_text += event["text"]
        elif etype == "thinking":
            thinking_text += event["text"]
        elif etype == "tool_call":
            _current_tool = event.get("tool", "")
            tool_log.append({"tool": _current_tool, "args": event.get("args", {}), "result": ""})
        elif etype == "tool_result" and tool_log:
            tool_log[-1]["result"] = str(event.get("output", ""))[:200]
        elif etype == "tool_denied" and tool_log:
            tool_log[-1]["result"] = "[denied by user]"
        yield event_json

    # Build new history: prior turns + current user input + full loop exchange
    # Strip base64 image data from tool result messages to keep Qdrant storage lean
    def _strip_images(turn: dict) -> dict:
        content = turn.get("content")
        if isinstance(content, list):
            stripped = []
            for block in content:
                if block.get("type") == "image_url":
                    stripped.append({"type": "text", "text": "[image omitted from history]"})
                else:
                    stripped.append(block)
            return {**turn, "content": stripped}
        return turn

    # Build condensed tool log so the model knows what it did in previous turns
    saved_content = response_text
    if tool_log:
        lines = []
        for entry in tool_log:
            args_str = json.dumps(entry["args"], ensure_ascii=False)
            if len(args_str) > 120:
                args_str = args_str[:120] + "..."
            result_str = entry["result"]
            if len(result_str) > 150:
                result_str = result_str[:150] + "..."
            lines.append(f"- {entry['tool']}({args_str}) → {result_str}")
        saved_content += "\n\n<tool_history>\n" + "\n".join(lines) + "\n</tool_history>"

    final_assistant = None
    for turn in reversed(messages[loop_start:]):
        if turn.get("role") == "assistant":
            final_assistant = _strip_images({**turn, "content": saved_content, "thoughts": thinking_text})
            break

    new_history = chat_history + [{"role": "user", "content": chat_input}]
    if final_assistant:
        new_history.append(final_assistant)
    await save_session(session_id, new_history)
    extract_after_response(chat_input, response_text)
    tool_stats.record_session_end(session_id)
    log.info("run_chat done: session=%s  %.1fs  response_len=%d", session_id, time.monotonic() - req_t0, len(response_text))
