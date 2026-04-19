import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from memory.facts import search_facts, search_procedures
from memory.sources import search_sources
from memory.profile import get_profile
from memory.sessions import load_session, save_session
from memory.extraction import extract_after_response
from curator.preflight import run_preflight, get_thinking_budget
from router.classifier import RouteDecision
from tools.llm import chat_complete

SYSTEM_TEMPLATE = """You are {personality}, an AI assistant.
Date/time: {datetime}
Context: {context_state}

User profile:
{profile}

Relevant facts:
{facts}

Relevant procedures:
{procedures}

Relevant knowledge:
{sources}"""


async def run_chat(
    chat_input: str,
    chat_history: list[dict],
    session_id: str,
    images: list[dict] | None = None,
    route: RouteDecision | None = None,
) -> AsyncGenerator[str, None]:
    # load server session if client sent empty history
    if not chat_history:
        chat_history = await load_session(session_id)

    profile = await get_profile()
    context_state = profile.get("context_state", "free")

    # pre-flight
    preflight = await run_preflight(
        recent_turns=chat_history[-3:],
        current_personality=profile.get("current_personality", "Casual"),
        context_state=context_state,
    )
    personality = preflight["personality"]
    thinking_depth = preflight["thinking_depth"]
    budget = get_thinking_budget(thinking_depth)

    # memory retrieval — skip if router flagged useRetrieval=False
    use_retrieval = route.use_retrieval if route else True
    if use_retrieval:
        facts, procedures, sources = await asyncio.gather(
            search_facts(chat_input, top_k=5),
            search_procedures(chat_input, top_k=4),
            search_sources(chat_input, top_k=5),
        )
    else:
        facts, procedures, sources = [], [], []

    facts_text = "\n".join(f"- {f.get('text', '')}" for f in facts) or "None"
    proc_text = "\n".join(f"- {p.get('text', '')}" for p in procedures) or "None"
    sources_text = "\n".join(f"- {s.get('text', s.get('content', ''))[:300]}" for s in sources) or "None"
    profile_text = json.dumps({k: v for k, v in profile.items() if k != "context_state"}, indent=2)

    system = SYSTEM_TEMPLATE.format(
        personality=personality,
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
        context_state=context_state,
        profile=profile_text,
        facts=facts_text,
        procedures=proc_text,
        sources=sources_text,
    )

    # build messages
    messages = [{"role": "system", "content": system}]
    for turn in chat_history[-40:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # add current user message (with images if present)
    if images:
        user_content = [{"type": "text", "text": chat_input}]
        for img in images:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{img['type']};base64,{img['base64']}"},
            })
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": chat_input})

    # call model
    kwargs = {}
    if budget is not None:
        kwargs["extra_body"] = {"thinking_budget_tokens": budget}

    response_text = ""
    thinking_text = ""

    async for chunk in await chat_complete(messages, stream=True, **kwargs):
        choice = chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})

        if delta.get("reasoning_content"):
            thinking_text += delta["reasoning_content"]
            yield json.dumps({"type": "thinking", "text": delta["reasoning_content"]})

        if delta.get("content"):
            response_text += delta["content"]
            yield json.dumps({"type": "text", "text": delta["content"]})

    # save session + fire post-response extraction in parallel
    new_history = chat_history + [
        {"role": "user", "content": chat_input},
        {"role": "assistant", "content": response_text, "thoughts": thinking_text},
    ]
    await save_session(session_id, new_history)
    extract_after_response(chat_input, response_text)
