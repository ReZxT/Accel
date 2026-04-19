import re
import httpx
from config import config

SEARXNG_URL = "http://localhost:8888"
PLAYWRIGHT_URL = "http://localhost:9300"
MAX_TEXT = 12_000
MAX_HTML = 50_000


async def search_web(query: str, num_results: int = 8) -> str:
    """Search the web via SearXNG (aggregates Bing, DuckDuckGo, Brave, Google)."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json", "language": "en"},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Search failed: {e}"

    results = data.get("results", [])[:num_results]
    if not results:
        return "No results found."

    lines = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("content", "")
        lines.append(f"**{title}**\n{url}\n{snippet}")

    return "\n\n---\n\n".join(lines)


async def fetch_url(url: str) -> str:
    """Fetch a URL and return its readable text content (HTML stripped)."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            )
            r.raise_for_status()
            html = r.text
    except Exception as e:
        return f"Fetch failed: {e}"

    # strip tags with regex (avoids bs4 dependency)
    text = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>[\s\S]*?</\1>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    text = "\n".join(lines)

    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + "\n\n[truncated]"

    return text or "No readable content found."


async def screenshot_url(url: str, full_page: bool = False) -> dict:
    """Take a screenshot of a web page. Returns image dict for vision model."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{PLAYWRIGHT_URL}/screenshot",
                json={"url": url, "full_page": full_page},
                timeout=45,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {"__type": "error", "text": f"Screenshot failed: {e}"}

    b64 = data.get("image_base64", "")
    if not b64:
        return {"__type": "error", "text": "Screenshot returned empty image."}

    return {"__type": "image", "base64": b64, "mime_type": "image/png", "url": url}
