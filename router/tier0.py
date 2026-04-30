"""Tier 0 intent classification — regex/rule-based fast filter before model inference.

Returns an intent that short-circuits or optimizes the pipeline:
- GREETING / ACKNOWLEDGMENT → canned response, skip model entirely
- BARE_URL → hint to fetch, skip memory retrieval
- MEMORY_SAVE → hint to route to memory tools, skip heavy retrieval
- CASUAL → skip preflight curator, use Casual/light defaults
- None → no match, proceed normally through router + preflight
"""

import logging
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

# -- patterns --

_GREETING = re.compile(
    r"^(hi|hey|hello|yo|sup|what'?s up|howdy|good (morning|afternoon|evening)|hej|cześć|siema|elo)\s*[!?.,]*$",
    re.IGNORECASE,
)

_ACKNOWLEDGMENT = re.compile(
    r"^(ok|okay|thanks|thank you|thx|ty|got it|understood|cool|nice|great|sure|alright|right"
    r"|dzięki|dzięks|spoko|jasne|no ok|okej|dobra)\s*[!?.,]*$",
    re.IGNORECASE,
)

_FAREWELL = re.compile(
    r"^(bye|goodbye|good night|gn|see you|later|cya|nara|pa|dobranoc)\s*[!?.,]*$",
    re.IGNORECASE,
)

_BARE_URL = re.compile(
    r"^https?://\S+$",
    re.IGNORECASE,
)

_MEMORY_SAVE = re.compile(
    r"^(remember|zapamiętaj)\s+.+",
    re.IGNORECASE,
)

_MEMORY_FORGET = re.compile(
    r"^(forget|zapomnij)\s+.+",
    re.IGNORECASE,
)

_CASUAL_SHORT = re.compile(
    r"^.{1,15}[?!.]?$",
)


@dataclass
class Tier0Result:
    intent: str
    canned_response: str | None = None
    skip_preflight: bool = False
    skip_retrieval: bool = False
    force_personality: str | None = None
    force_thinking_depth: str | None = None


_GREETING_RESPONSES = [
    "Hey! What can I help with?",
    "Hi! What's on your mind?",
    "Hey, what's up?",
]

_ACK_RESPONSES = [
    "Got it.",
    "Alright.",
    "Sure thing.",
]

_FAREWELL_RESPONSES = [
    "See you!",
    "Later!",
    "Bye!",
]

_response_idx = 0


def _pick_response(pool: list[str]) -> str:
    global _response_idx
    r = pool[_response_idx % len(pool)]
    _response_idx += 1
    return r


def classify_tier0(text: str, has_images: bool = False, has_files: bool = False) -> Tier0Result | None:
    """Fast rule-based classification. Returns None if no match (fall through to full pipeline)."""
    if has_images or has_files:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    if _GREETING.match(stripped):
        log.info("tier0: GREETING")
        return Tier0Result(
            intent="greeting",
            canned_response=_pick_response(_GREETING_RESPONSES),
            skip_preflight=True,
            skip_retrieval=True,
        )

    if _ACKNOWLEDGMENT.match(stripped):
        log.info("tier0: ACKNOWLEDGMENT")
        return Tier0Result(
            intent="acknowledgment",
            canned_response=_pick_response(_ACK_RESPONSES),
            skip_preflight=True,
            skip_retrieval=True,
        )

    if _FAREWELL.match(stripped):
        log.info("tier0: FAREWELL")
        return Tier0Result(
            intent="farewell",
            canned_response=_pick_response(_FAREWELL_RESPONSES),
            skip_preflight=True,
            skip_retrieval=True,
        )

    if _BARE_URL.match(stripped):
        log.info("tier0: BARE_URL")
        return Tier0Result(
            intent="bare_url",
            skip_preflight=True,
            skip_retrieval=True,
            force_personality="Casual",
            force_thinking_depth="none",
        )

    if _MEMORY_SAVE.match(stripped):
        log.info("tier0: MEMORY_SAVE")
        return Tier0Result(
            intent="memory_save",
            skip_preflight=True,
            skip_retrieval=True,
            force_personality="Casual",
            force_thinking_depth="light",
        )

    if _MEMORY_FORGET.match(stripped):
        log.info("tier0: MEMORY_FORGET")
        return Tier0Result(
            intent="memory_forget",
            skip_preflight=True,
            skip_retrieval=True,
            force_personality="Casual",
            force_thinking_depth="light",
        )

    if _CASUAL_SHORT.match(stripped) and not any(c in stripped for c in "{}[]()<>|`"):
        log.info("tier0: CASUAL_SHORT")
        return Tier0Result(
            intent="casual_short",
            skip_preflight=True,
            force_personality="Casual",
            force_thinking_depth="light",
        )

    return None
