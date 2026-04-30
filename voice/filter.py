import re

# Maps tool names to spoken status lines
TOOL_PHRASES = {
    "search_web":         "Let me search for that...",
    "fetch_url":          "Let me fetch that page...",
    "screenshot_url":     "Let me take a screenshot...",
    "search_knowledge_base": "Let me check the knowledge base...",
    "search_notes":       "Let me look through the notes...",
    "read_file":          "Let me read that file...",
    "bash":               "Let me run that...",
    "search_files":       "Let me search the files...",
    "list_dir":           "Let me check that directory...",
    "calculate":          "Let me calculate that...",
    "convert_units":      "Let me convert that...",
    "convert_currency":   "Let me check the exchange rate...",
    "calendar_get_events":"Let me check the calendar...",
    "calendar_add_event": "Let me add that to the calendar...",
    "search_audiobooks":  "Let me search for that audiobook...",
}
DEFAULT_TOOL_PHRASE = "Let me work on that..."

VOICE_SYSTEM_ADDENDUM = """

[VOICE MODE] Respond in 1–3 concise spoken sentences unless the user explicitly asks to explain or expand. No markdown, no bullet points, no code blocks. Natural spoken language only."""


def tool_phrase(tool_name: str) -> str:
    return TOOL_PHRASES.get(tool_name, DEFAULT_TOOL_PHRASE)


def filter_response(text: str) -> str:
    """Strip markdown and thinking artifacts from a response for TTS."""
    # strip <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # strip markdown bold/italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # strip markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # strip code blocks
    text = re.sub(r"```.*?```", "code block omitted", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    # strip URLs
    text = re.sub(r"https?://\S+", "", text)
    # collapse whitespace
    text = re.sub(r"\n{2,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
