import json
import httpx
from typing import AsyncGenerator
from config import config


async def chat_complete(messages: list[dict], stream: bool = False, **kwargs) -> dict | AsyncGenerator:
    payload = {
        "model": config.chat_model,
        "messages": messages,
        "stream": stream,
        **kwargs,
    }
    if stream:
        return _stream_chat(payload)
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{config.chat_url}/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()


async def _stream_chat(payload: dict) -> AsyncGenerator[dict, None]:
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


async def curator_complete(messages: list[dict], temperature: float = 0.1) -> str:
    payload = {
        "model": config.curator_model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{config.curator_url}/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{config.embed_url}/embeddings",
            json={"model": config.embed_model, "input": text},
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
