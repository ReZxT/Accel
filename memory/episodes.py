import time
import uuid
from qdrant_client.models import PointStruct
from memory.facts import get_client
from tools.llm import embed, curator_complete

COMPRESS_THRESHOLD = 50  # turns before compression triggers
KEEP_RECENT = 20         # turns to keep after compression

SUMMARY_PROMPT = """Summarize the following conversation exchange into a concise episode memory.
Capture: main topics discussed, decisions made, key facts learned, and outcomes.
Be factual and specific. Write 2-5 sentences.

{turns}

Summary:"""


async def maybe_compress(session_id: str, history: list[dict]) -> list[dict]:
    """If history exceeds threshold, compress old turns into episodes and return trimmed history."""
    if len(history) <= COMPRESS_THRESHOLD:
        return history

    old_turns = history[:-KEEP_RECENT]
    recent_turns = history[-KEEP_RECENT:]

    # Format old turns for summarization
    lines = []
    for turn in old_turns:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            lines.append(f"{role.upper()}: {content[:500]}")

    if not lines:
        return recent_turns

    turns_text = "\n".join(lines)
    prompt = SUMMARY_PROMPT.format(turns=turns_text)

    try:
        summary = await curator_complete([{"role": "user", "content": prompt}])
        summary = summary.strip()
    except Exception:
        return recent_turns

    # Store episode in Qdrant
    try:
        vector = await embed(summary)
        point_id = str(uuid.uuid4())
        await get_client().upsert(
            collection_name="episodes",
            points=[PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "text": summary,
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "turn_count": len(old_turns),
                    "source": "compression",
                },
            )],
        )
    except Exception:
        pass

    return recent_turns
