import asyncio
import json
import re
import uuid
import httpx
from datetime import datetime
from typing import AsyncGenerator

from memory.facts import search_facts, search_procedures
from memory.sources import search_sources
from memory.notes import search_notes
from memory.profile import get_profile, get_tool_settings
from memory.sessions import load_session, save_session
from memory.extraction import extract_after_response
from memory.episodes import maybe_compress
from curator.preflight import run_preflight, get_thinking_budget
from router.classifier import RouteDecision
from tools.llm import chat_complete
from tools.tool_parser import parse_xml_tool_calls, strip_tool_calls
from tools.tool_descriptions import TOOLS_SYSTEM_BLOCK
from tools.code_tools import execute_tool, IRREVERSIBLE_TOOLS
from tools import approval
from config import config

MAX_TOOL_ITERATIONS = 25
TOOL_CONTINUE_BATCH = 25

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
) -> AsyncGenerator[str, None]:
    """Streaming agentic loop: call model, parse tool calls, execute, repeat."""
    nudged = False
    iterations = 0
    while True:
        response_text = ""
        thinking_text = ""

        # stream model response — buffer text, stream thinking live
        async for chunk in await chat_complete(messages, stream=True, **budget_kwargs):
            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            if delta.get("reasoning_content"):
                thinking_text += delta["reasoning_content"]
                yield json.dumps({"type": "thinking", "text": delta["reasoning_content"]})
            if delta.get("content"):
                response_text += delta["content"]

        # extract <think> blocks from content field (DIMOE sometimes puts thinking there)
        think_blocks = re.findall(r"<think>([\s\S]*?)</think>", response_text, re.IGNORECASE)
        if think_blocks:
            extra_thinking = "\n".join(think_blocks).strip()
            if extra_thinking:
                thinking_text += extra_thinking
                yield json.dumps({"type": "thinking", "text": extra_thinking})
            response_text = re.sub(r"<think>[\s\S]*?</think>", "", response_text, flags=re.IGNORECASE).strip()

        tool_calls = parse_xml_tool_calls(response_text)
        clean_text = strip_tool_calls(response_text) if tool_calls else response_text

        # emit clean text (strips XML tool call markup)
        if clean_text:
            yield json.dumps({"type": "text", "text": clean_text})

        # Build assistant content — embed thinking so it stays in context
        def _assistant_content(text: str, thinking: str) -> str:
            if thinking:
                return f"<think>{thinking}</think>\n{text}" if text else f"<think>{thinking}</think>"
            return text

        if not tool_calls:
            # model produced no text and no tool calls — nudge once then stop
            if not clean_text and not nudged:
                nudged = True
                messages.append({"role": "assistant", "content": ""})
                messages.append({"role": "user", "content": "Please provide your response."})
                continue
            # Append final response to messages so run_chat can save the full exchange
            messages.append({"role": "assistant", "content": _assistant_content(response_text, thinking_text)})
            break

        iterations += 1
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

            tool_task = asyncio.create_task(execute_tool(tool_name, tool_args))
            while not tool_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(tool_task), timeout=15)
                except asyncio.TimeoutError:
                    yield json.dumps({"type": "heartbeat"})
            result = tool_task.result()

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
) -> AsyncGenerator[str, None]:
    if not chat_history:
        chat_history = await load_session(session_id)

    chat_history = await maybe_compress(session_id, chat_history)

    profile = await get_profile()
    context_state = profile.get("context_state", "free")
    tool_settings = await get_tool_settings()

    preflight = await run_preflight(
        recent_turns=chat_history[-3:],
        current_personality=profile.get("current_personality", "Casual"),
        context_state=context_state,
    )
    personality = preflight["personality"]
    thinking_depth = preflight["thinking_depth"]
    budget = get_thinking_budget(thinking_depth)

    use_retrieval = route.use_retrieval if route else True
    if use_retrieval:
        facts, procedures, sources, notes = await asyncio.gather(
            search_facts(chat_input, top_k=5),
            search_procedures(chat_input, top_k=4),
            search_sources(chat_input, top_k=3),
            search_notes(chat_input, top_k=3),
        )
    else:
        facts, procedures, sources, notes = [], [], [], []

    facts_text = "\n".join(f"- {f.get('text', '')}" for f in facts) or "None"
    proc_text = "\n".join(f"- {p.get('text', '')}" for p in procedures) or "None"

    def _fmt_source(s: dict) -> str:
        title = s.get("title", "")
        filepath = s.get("filepath", "")
        text = s.get("text", s.get("content", ""))[:300]
        label = f"[{title} — {filepath}]" if filepath else (f"[{title}]" if title else "")
        return f"{label} {text}".strip()

    sources_text = "\n".join(f"- {_fmt_source(s)}" for s in sources) or "None"
    notes_text = "\n".join(f"- {_fmt_source(n)}" for n in notes) or "None"
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
        tools_block=TOOLS_SYSTEM_BLOCK,
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

    budget_kwargs = {}
    if budget is not None:
        budget_kwargs["extra_body"] = {"thinking_budget_tokens": budget}

    # agentic loop — accumulate final response text for extraction/display
    response_text = ""
    thinking_text = ""

    async for event_json in _run_agentic_loop(messages, budget_kwargs, session_id, tool_settings):
        event = json.loads(event_json)
        if event["type"] == "text":
            response_text += event["text"]
        elif event["type"] == "thinking":
            thinking_text += event["text"]
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

    # Only save the final assistant message — skip intermediate tool-call/result turns
    # so server and client history stay the same length and pollSession doesn't misfire.
    final_assistant = None
    for turn in reversed(messages[loop_start:]):
        if turn.get("role") == "assistant":
            final_assistant = _strip_images({**turn, "content": response_text, "thoughts": thinking_text})
            break

    new_history = chat_history + [{"role": "user", "content": chat_input}]
    if final_assistant:
        new_history.append(final_assistant)
    await save_session(session_id, new_history)
    extract_after_response(chat_input, response_text)
