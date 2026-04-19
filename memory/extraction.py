import json
import time
import uuid
import asyncio
from qdrant_client.models import PointStruct
from memory.facts import get_client
from tools.llm import curator_complete, embed

FACT_PROMPT = """Extract factual statements about the user from this conversation.
Return a JSON array of strings. Each string is one fact about the user — their preferences, work, life, knowledge, or goals.
Only include genuinely informative facts. Return [] if nothing notable.

USER: {user_msg}
ASSISTANT: {assistant_msg}

Return only a valid JSON array of strings."""

PROCEDURE_PROMPT = """Extract interaction patterns from this conversation exchange.
Return a JSON array of strings. Each string describes a pattern about how this user likes to work, learn, or communicate.
Focus on: communication style, learning preferences, what approaches worked well.
Return [] if nothing notable.

USER: {user_msg}
ASSISTANT: {assistant_msg}

Return only a valid JSON array of strings."""


async def _extract_and_save(collection: str, prompt: str) -> None:
    try:
        raw = await curator_complete([{"role": "user", "content": prompt}])
        raw = raw.strip().strip("```json").strip("```").strip()
        items = json.loads(raw)
        if not isinstance(items, list) or not items:
            return
        await _upsert_items(collection, [str(i) for i in items if i])
    except Exception:
        pass


async def _upsert_items(collection: str, texts: list[str]) -> None:
    points = []
    for text in texts:
        vector = await embed(text)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, text))
        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload={"text": text, "timestamp": time.time(), "source": "conversation"},
        ))
    if points:
        await get_client().upsert(collection_name=collection, points=points)


def extract_after_response(user_msg: str, assistant_msg: str) -> None:
    """Fire-and-forget post-response extraction. Call after streaming completes."""
    fact_prompt = FACT_PROMPT.format(user_msg=user_msg, assistant_msg=assistant_msg[:1000])
    proc_prompt = PROCEDURE_PROMPT.format(user_msg=user_msg, assistant_msg=assistant_msg[:1000])
    asyncio.create_task(_extract_and_save("facts", fact_prompt))
    asyncio.create_task(_extract_and_save("procedures", proc_prompt))
