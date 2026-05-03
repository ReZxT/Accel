"""Backend clients — HTTP dispatch for each model provider.

All callers use the top-level functions (chat_complete, curator_complete,
embed_text). These look up the active model in the registry and route to
the correct provider client.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import httpx

from .registry import registry, ModelDef
from circuit_breaker import breakers

log = logging.getLogger(__name__)


# ============================================================================
# OpenAI-compatible chat (llama_cpp + openai providers)
# ============================================================================

async def _openai_chat(
    model: ModelDef,
    messages: list[dict],
    stream: bool = False,
    **kwargs,
) -> dict | AsyncGenerator:
    """Call an OpenAI-compatible /v1/chat/completions endpoint."""
    payload = {
        "model": model.model_name,
        "messages": messages,
        "stream": stream,
        **kwargs,
    }
    # Merge extra_body from model definition (e.g. thinking_budget_tokens)
    if model.extra_body:
        payload.setdefault("extra_body", {}).update(model.extra_body)
        # OpenAI uses top-level keys for some params, llama.cpp uses extra_body
        if model.provider == "openai":
            payload.update(model.extra_body)

    headers = {"Content-Type": "application/json", **model.auth_header, **model.extra_headers}

    if stream:
        return _stream_openai(model, payload, headers)
    else:
        return await _sync_openai(model, payload, headers)


async def _sync_openai(model: ModelDef, payload: dict, headers: dict) -> dict:
    cb = breakers.get("chat_model", breakers.get("chat"))
    if cb and not cb.can_execute():
        raise ConnectionError(f"Chat model circuit is open for {model.id}")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{model.endpoint}/chat/completions",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            if cb:
                cb.record_success()
            return r.json()
    except Exception:
        if cb:
            cb.record_failure()
        raise


async def _stream_openai(
    model: ModelDef,
    payload: dict,
    headers: dict,
) -> AsyncGenerator[dict, None]:
    cb = breakers.get("chat_model", breakers.get("chat"))
    if cb and not cb.can_execute():
        raise ConnectionError(f"Chat model circuit is open for {model.id}")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{model.endpoint}/chat/completions",
                json=payload,
                headers=headers,
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        pass
        if cb:
            cb.record_success()
    except Exception:
        if cb:
            cb.record_failure()
        raise


# ============================================================================
# Anthropic Messages API
# ============================================================================

def _convert_to_anthropic(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Convert OpenAI-format messages to Anthropic format.

    Returns (system_text, anthropic_messages).
    Anthropic has system as a top-level param, not a message role.
    """
    system_parts = []
    anthropic_msgs = []

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")

        if role == "system":
            system_parts.append(content if isinstance(content, str) else str(content))
            continue

        # Handle multimodal content (list of blocks)
        if isinstance(content, list):
            anthropic_content = []
            for block in content:
                if block.get("type") == "text":
                    anthropic_content.append({"type": "text", "text": block["text"]})
                elif block.get("type") == "image_url":
                    url = block.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        # data:image/png;base64,XXXXX
                        media_type = url.split(";")[0].split(":")[1] if ";" in url else "image/png"
                        b64 = url.split(",", 1)[1] if "," in url else ""
                        anthropic_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        })
            anthropic_msgs.append({"role": role, "content": anthropic_content})
        else:
            anthropic_msgs.append({"role": role, "content": str(content)})

    system = "\n".join(system_parts) if system_parts else None
    return system, anthropic_msgs


async def _anthropic_chat(
    model: ModelDef,
    messages: list[dict],
    stream: bool = False,
    **kwargs,
) -> dict | AsyncGenerator:
    """Call Anthropic Messages API."""
    system, anthropic_msgs = _convert_to_anthropic(messages)

    max_tokens = kwargs.pop("max_tokens", 16384)

    payload = {
        "model": model.model_name,
        "messages": anthropic_msgs,
        "max_tokens": max_tokens,
        "stream": stream,
        **model.extra_body,
    }
    if system:
        payload["system"] = system

    # Map OpenAI-style params to Anthropic
    if "temperature" in kwargs:
        payload["temperature"] = kwargs.pop("temperature")
    if "top_p" in kwargs:
        payload["top_p"] = kwargs.pop("top_p")

    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "output-128k-2025-02-19",
        **model.auth_header,
        **model.extra_headers,
    }

    if model.supports_thinking:
        headers["anthropic-beta"] += ",extended-thinking-2025-05-07"

    if stream:
        return _stream_anthropic(model, payload, headers)
    else:
        return await _sync_anthropic(model, payload, headers)


async def _sync_anthropic(model: ModelDef, payload: dict, headers: dict) -> dict:
    cb = breakers.get("chat_model", breakers.get("chat"))
    if cb and not cb.can_execute():
        raise ConnectionError(f"Chat model circuit is open for {model.id}")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{model.endpoint}/messages",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            if cb:
                cb.record_success()
            # Convert Anthropic response to OpenAI-compatible format
            return _anthropic_to_openai(r.json())
    except Exception:
        if cb:
            cb.record_failure()
        raise


async def _stream_anthropic(
    model: ModelDef,
    payload: dict,
    headers: dict,
) -> AsyncGenerator[dict, None]:
    cb = breakers.get("chat_model", breakers.get("chat"))
    if cb and not cb.can_execute():
        raise ConnectionError(f"Chat model circuit is open for {model.id}")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{model.endpoint}/messages",
                json=payload,
                headers=headers,
            ) as r:
                r.raise_for_status()
                # Accumulate SSE events, convert to OpenAI delta format
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                        openai_chunk = _anthropic_event_to_openai(event)
                        if openai_chunk:
                            yield openai_chunk
                    except json.JSONDecodeError:
                        pass
        if cb:
            cb.record_success()
    except Exception:
        if cb:
            cb.record_failure()
        raise


def _anthropic_to_openai(anthropic_resp: dict) -> dict:
    """Convert a sync Anthropic response to OpenAI-compatible format."""
    content = anthropic_resp.get("content", [])
    text_parts = []
    thinking_parts = []
    for block in content:
        if block.get("type") == "text":
            text_parts.append(block["text"])
        elif block.get("type") == "thinking":
            thinking_parts.append(block.get("thinking", ""))

    usage = anthropic_resp.get("usage", {})
    return {
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n".join(text_parts),
                "reasoning_content": "\n".join(thinking_parts) or None,
            },
            "finish_reason": anthropic_resp.get("stop_reason", "stop"),
        }],
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        },
    }


def _anthropic_event_to_openai(event: dict) -> dict | None:
    """Convert a streaming Anthropic SSE event to OpenAI delta format."""
    etype = event.get("type", "")
    if etype == "message_start":
        return {"choices": [{"index": 0, "delta": {"role": "assistant"}}]}
    elif etype == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta":
            return {"choices": [{"index": 0, "delta": {"content": delta.get("text", "")}}]}
        elif delta.get("type") == "thinking_delta":
            return {"choices": [{"index": 0, "delta": {"reasoning_content": delta.get("thinking", "")}}]}
    elif etype == "content_block_start":
        block = event.get("content_block", {})
        if block.get("type") == "thinking":
            return {"choices": [{"index": 0, "delta": {"reasoning_content": block.get("thinking", "")}}]}
    elif etype == "message_delta":
        usage = event.get("usage", {})
        delta = event.get("delta", {})
        result = {"choices": [{"index": 0, "delta": {}, "finish_reason": delta.get("stop_reason", "stop")}]}
        if usage:
            result["usage"] = {
                "prompt_tokens": 0,
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("output_tokens", 0),
            }
        return result
    return None


# ============================================================================
# Curator (small model for extraction / compression / preflight)
# ============================================================================

async def _llama_cpp_curator_complete(model: ModelDef, messages: list[dict], temperature: float = 0.1) -> str:
    """Raw /completion call used by the 0.8B Qwen curator.

    Injects <think></think> to suppress thinking on models where
    thinking_budget_tokens=0 is broken.
    """
    cb = breakers.get("curator_model", breakers.get("curator"))
    if cb and not cb.can_execute():
        return ""

    parts = []
    for m in messages:
        role = m["role"]
        content = m.get("content", "")
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    parts.append("<|im_start|>assistant\n<think>\n</think>\n")
    prompt = "\n".join(parts)

    payload = {
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": temperature,
        "stop": ["<|im_end|>"],
        "stream": False,
    }
    base_url = model.endpoint.removesuffix("/v1")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{base_url}/completion", json=payload)
            r.raise_for_status()
            if cb:
                cb.record_success()
            return r.json().get("content", "")
    except Exception:
        if cb:
            cb.record_failure()
        return ""


async def _openai_curator_complete(model: ModelDef, messages: list[dict], temperature: float = 0.1) -> str:
    """Use the chat completions endpoint for curator tasks (fallback for non-llama.cpp)."""
    try:
        result = await _sync_openai(
            model,
            {
                "model": model.model_name,
                "messages": messages,
                "max_tokens": 512,
                "temperature": temperature,
                "stream": False,
            },
            {
                "Content-Type": "application/json",
                **model.auth_header,
                **model.extra_headers,
            },
        )
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        return ""


# ============================================================================
# Embeddings
# ============================================================================

async def _openai_embed(model: ModelDef, text: str) -> list[float]:
    cb = breakers.get("embeddings")
    if cb and not cb.can_execute():
        raise ConnectionError("Embeddings circuit is open")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{model.endpoint}/embeddings",
                json={"model": model.model_name, "input": text},
                headers={"Content-Type": "application/json", **model.auth_header},
            )
            r.raise_for_status()
            if cb:
                cb.record_success()
            return r.json()["data"][0]["embedding"]
    except Exception:
        if cb:
            cb.record_failure()
        raise


# ============================================================================
# Public API — the functions everyone imports
# ============================================================================

async def chat_complete(
    messages: list[dict],
    stream: bool = False,
    model_id: str | None = None,
    **kwargs,
) -> dict | AsyncGenerator:
    """Chat completion — routes to the right backend based on active model.

    If model_id is provided, it overrides the session-level active chat model
    for this single call.
    """
    model = registry.get(model_id) if model_id else registry.chat

    if model.provider in ("llama_cpp", "openai"):
        return await _openai_chat(model, messages, stream=stream, **kwargs)
    elif model.provider == "anthropic":
        return await _anthropic_chat(model, messages, stream=stream, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {model.provider}")


async def curator_complete(
    messages: list[dict],
    temperature: float = 0.1,
    model_id: str | None = None,
) -> str:
    """Curator completion — small/fast model for extraction and compression."""
    model = registry.get(model_id) if model_id else registry.curator

    if model.provider == "llama_cpp":
        return await _llama_cpp_curator_complete(model, messages, temperature)
    elif model.provider in ("openai", "anthropic"):
        return await _openai_curator_complete(model, messages, temperature)
    else:
        raise ValueError(f"Unknown provider for curator: {model.provider}")


async def embed_text(text: str, model_id: str | None = None) -> list[float]:
    """Embed text using the active embeddings model."""
    model = registry.get(model_id) if model_id else registry.embeddings
    return await _openai_embed(model, text)
