import json
import logging
from tools.llm import curator_complete

log = logging.getLogger(__name__)

PERSONALITIES = ["Teacher", "Coder", "Philosopher", "Casual", "Critic", "Mentor"]
THINKING_DEPTHS = ["none", "light", "medium", "deep"]

THINKING_BUDGETS = {
    "none": None,
    "light": 512,
    "medium": 4096,
    "deep": 16384,
}

PREFLIGHT_PROMPT = """You are a pre-flight coordinator for an AI assistant. Based on the conversation context, decide:
1. personality: one of {personalities}
2. thinking_depth: one of {depths}

Context state: {context_state}
Current personality: {current_personality}
Recent turns:
{recent_turns}

Respond with ONLY valid JSON: {{"personality": "...", "thinking_depth": "..."}}"""


async def run_preflight(
    recent_turns: list[dict],
    current_personality: str = "Casual",
    context_state: str = "free",
) -> dict:
    turns_text = "\n".join(
        f"{m['role'].upper()}: {str(m.get('content', ''))[:200]}"
        for m in recent_turns[-3:]
    )
    prompt = PREFLIGHT_PROMPT.format(
        personalities=", ".join(PERSONALITIES),
        depths=", ".join(THINKING_DEPTHS),
        context_state=context_state,
        current_personality=current_personality,
        recent_turns=turns_text or "(none)",
    )
    try:
        response = await curator_complete([{"role": "user", "content": prompt}])
        # strip markdown fences if present
        response = response.strip().strip("```json").strip("```").strip()
        result = json.loads(response)
        personality = result.get("personality", current_personality)
        depth = result.get("thinking_depth", "light")
        if personality not in PERSONALITIES:
            personality = current_personality
        if depth not in THINKING_DEPTHS:
            depth = "light"
        log.info("preflight: personality=%s  depth=%s", personality, depth)
        return {"personality": personality, "thinking_depth": depth}
    except Exception:
        log.warning("preflight failed — using defaults: %s/light", current_personality)
        return {"personality": current_personality, "thinking_depth": "light"}


def get_thinking_budget(depth: str) -> int | None:
    return THINKING_BUDGETS.get(depth)
