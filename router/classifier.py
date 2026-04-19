import re
from dataclasses import dataclass, field
from tools.llm import curator_complete

# ── Size thresholds (chars) ──────────────────────────────────────────────────
SIZE_SHORT  = 500
SIZE_MEDIUM = 2_000
SIZE_LONG   = 8_000

# ── Code detection patterns ──────────────────────────────────────────────────
CODE_EXTENSIONS = {
    "py", "js", "ts", "jsx", "tsx", "go", "rs", "c", "cpp", "h", "java",
    "json", "yaml", "yml", "toml", "xml", "css", "html", "sh", "sql", "md",
    "svg",
}
CODE_PATTERNS = re.compile(
    r"(def |class |import |from .+ import|function |const |let |var |=>"
    r"|async def|async function|\bif \(|\bfor \(|<\?xml|<!DOCTYPE"
    r"|^\s*\{|\[.*\]|\bSELECT\b|\bCREATE TABLE\b)",
    re.MULTILINE,
)
LOG_PATTERNS = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"|\b(ERROR|WARN|INFO|DEBUG|CRITICAL|FATAL|TRACE)\b"
    r"|Traceback \(most recent call last\)"
    r"|at \w+\.\w+\([\w.]+:\d+\))",
    re.MULTILINE,
)
CHAT_DUMP_PATTERNS = re.compile(
    r"^(\[?\d{1,2}[:/]\d{2}|\d{4}-\d{2}-\d{2}).{0,30}:[\s\S]{1,500}",
    re.MULTILINE,
)


@dataclass
class RouteDecision:
    route_family: str          # direct_chat | multimodal | preprocessed_text
    text_type: str             # chat | code | logs | ocr | document | chat_dump | unknown
    pipeline: str              # structured_analysis | log_analysis | chat_dump_analysis | direct_chat | multimodal
    size_class: str            # none | short | medium | long | huge
    input_mode: str            # text_only | image_present | file_present | multimodal
    use_retrieval: bool = True
    needs_summarization: bool = False
    needs_long_processing: bool = False
    retrieval_after_preprocessing: bool = False
    nl_prefix: str = ""        # natural language prefix extracted from code/log inputs


def _size_class(text: str) -> str:
    n = len(text)
    if n == 0:      return "none"
    if n < SIZE_SHORT:   return "short"
    if n < SIZE_MEDIUM:  return "medium"
    if n < SIZE_LONG:    return "long"
    return "huge"


def _looks_like_code(text: str, language: str = "") -> bool:
    if language and language.lower() in CODE_EXTENSIONS:
        return True
    if language == "svg":
        return True
    match_count = len(CODE_PATTERNS.findall(text))
    return match_count >= 2


def _looks_like_logs(text: str) -> bool:
    return len(LOG_PATTERNS.findall(text)) >= 3


def _looks_like_chat_dump(text: str) -> bool:
    return len(CHAT_DUMP_PATTERNS.findall(text)) >= 3


def _extract_nl_prefix(text: str) -> str:
    """Extract leading natural-language lines before the first code-like line."""
    lines = text.splitlines()
    prefix_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if CODE_PATTERNS.search(stripped) or LOG_PATTERNS.search(stripped):
            break
        prefix_lines.append(stripped)
        if len(prefix_lines) >= 5:
            break
    return " ".join(prefix_lines)


async def classify(
    chat_input: str,
    images: list | None = None,
    files: list | None = None,
) -> RouteDecision:
    has_images = bool(images)
    has_files = bool(files)

    # ── inputMode ────────────────────────────────────────────────────────────
    if has_images and has_files:
        input_mode = "multimodal"
    elif has_images:
        input_mode = "image_present"
    elif has_files:
        input_mode = "file_present"
    else:
        input_mode = "text_only"

    # ── multimodal shortcut ───────────────────────────────────────────────────
    if has_images:
        is_placeholder = not chat_input.strip() or chat_input.strip().startswith("[")
        return RouteDecision(
            route_family="multimodal",
            text_type="chat",
            pipeline="multimodal",
            size_class=_size_class(chat_input),
            input_mode=input_mode,
            use_retrieval=not is_placeholder,
        )

    # ── file-based preprocessed_text ─────────────────────────────────────────
    if has_files:
        first_file = files[0]
        lang = first_file.get("language", "").lower()
        content = first_file.get("content", "")
        full_text = chat_input + "\n" + content

        if lang in CODE_EXTENSIONS or _looks_like_code(content, lang):
            text_type = "code"
            pipeline = "structured_analysis"
        elif _looks_like_logs(content):
            text_type = "logs"
            pipeline = "log_analysis"
        else:
            text_type = "document"
            pipeline = "document_analysis"

        size = _size_class(full_text)
        return RouteDecision(
            route_family="preprocessed_text",
            text_type=text_type,
            pipeline=pipeline,
            size_class=size,
            input_mode=input_mode,
            use_retrieval=True,
            needs_summarization=size == "huge",
            needs_long_processing=size in ("long", "huge"),
            retrieval_after_preprocessing=True,
            nl_prefix=_extract_nl_prefix(chat_input),
        )

    # ── text-only classification ──────────────────────────────────────────────
    text = chat_input.strip()
    size = _size_class(text)

    if _looks_like_logs(text):
        return RouteDecision(
            route_family="preprocessed_text",
            text_type="logs",
            pipeline="log_analysis",
            size_class=size,
            input_mode=input_mode,
            use_retrieval=True,
            needs_long_processing=size in ("long", "huge"),
            retrieval_after_preprocessing=True,
            nl_prefix=_extract_nl_prefix(text),
        )

    if _looks_like_code(text):
        return RouteDecision(
            route_family="preprocessed_text",
            text_type="code",
            pipeline="structured_analysis",
            size_class=size,
            input_mode=input_mode,
            use_retrieval=True,
            needs_long_processing=size in ("long", "huge"),
            retrieval_after_preprocessing=True,
            nl_prefix=_extract_nl_prefix(text),
        )

    if _looks_like_chat_dump(text):
        return RouteDecision(
            route_family="preprocessed_text",
            text_type="chat_dump",
            pipeline="chat_dump_analysis",
            size_class=size,
            input_mode=input_mode,
            use_retrieval=False,
            needs_summarization=size in ("long", "huge"),
        )

    # huge unclassified text — document path
    if size == "huge":
        return RouteDecision(
            route_family="preprocessed_text",
            text_type="document",
            pipeline="document_analysis",
            size_class=size,
            input_mode=input_mode,
            use_retrieval=False,
            needs_summarization=True,
            needs_long_processing=True,
        )

    # direct chat (short/medium/long plain text)
    return RouteDecision(
        route_family="direct_chat",
        text_type="chat",
        pipeline="direct_chat",
        size_class=size,
        input_mode=input_mode,
        use_retrieval=True,
    )
