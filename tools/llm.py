import json
import httpx
from typing import AsyncGenerator
from config import config
from circuit_breaker import breakers


async def chat_complete(messages: list[dict], stream: bool = False, **kwargs) -> dict | AsyncGenerator:
    payload = {
        "model": config.chat_model,
        "messages": messages,
        "stream": stream,
        **kwargs,
    }
    if stream:
        return _stream_chat(payload)
    cb = breakers["chat"]
    if not cb.can_execute():
        raise ConnectionError("Chat model circuit is open")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{config.chat_url}/chat/completions", json=payload)
            r.raise_for_status()
            cb.record_success()
            return r.json()
    except Exception:
        cb.record_failure()
        raise


async def _stream_chat(payload: dict) -> AsyncGenerator[dict, None]:
    cb = breakers["chat"]
    if not cb.can_execute():
        raise ConnectionError("Chat model circuit is open")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{config.chat_url}/chat/completions", json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        pass
        cb.record_success()
    except Exception:
        cb.record_failure()
        raise


async def curator_complete(messages: list[dict], temperature: float = 0.1) -> str:
    # 0.8B thinking model: inject empty <think> block via raw /completion to skip reasoning
    cb = breakers["curator"]
    if not cb.can_execute():
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
    base_url = config.curator_url.removesuffix("/v1")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{base_url}/completion", json=payload)
            r.raise_for_status()
            cb.record_success()
            return r.json().get("content", "")
    except Exception:
        cb.record_failure()
        return ""


async def embed(text: str) -> list[float]:
    cb = breakers["embeddings"]
    if not cb.can_execute():
        raise ConnectionError("Embeddings circuit is open")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{config.embed_url}/embeddings",
                json={"model": config.embed_model, "input": text},
            )
            r.raise_for_status()
            cb.record_success()
            return r.json()["data"][0]["embedding"]
    except Exception:
        cb.record_failure()
        raise
