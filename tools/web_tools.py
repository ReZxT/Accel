import asyncio
import re
import httpx
from config import config
from memory.sources import search_sources
from memory.notes import search_notes as _search_notes
from memory.facts import get_client

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
        async with httpx.AsyncClient(follow_redirects=True) as probe:
            pr = await probe.head(
                url,
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            )
            if pr.status_code >= 400:
                return {"__type": "error", "text": f"URL returned {pr.status_code} — check the address and try again."}
    except Exception as e:
        return {"__type": "error", "text": f"URL unreachable: {e} — check the address and try again."}

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


async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """Search the ingested knowledge base (books, documents, Obsidian vault) using semantic search."""
    try:
        results = await search_sources(query, top_k=top_k, threshold=0.5)
    except Exception as e:
        return f"Knowledge base search failed: {e}"
    if not results:
        return "No relevant results found in the knowledge base."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title") or r.get("filename", "Unknown")
        section = r.get("section") or r.get("page") or ""
        section_str = f" — {section}" if section else ""
        text = r.get("text", "")[:600]
        lines.append(f"[{i}] **{title}**{section_str}\n{text}")
    return "\n\n---\n\n".join(lines)


async def search_notes(query: str, top_k: int = 5) -> str:
    """Search the Obsidian vault notes using semantic search."""
    try:
        results = await _search_notes(query, top_k=top_k, threshold=0.45)
    except Exception as e:
        return f"Notes search failed: {e}"
    if not results:
        return "No relevant notes found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title") or r.get("filename", "Unknown")
        filepath = r.get("filepath", "")
        section = r.get("section", "")
        label = title
        if filepath and filepath != title:
            label += f" ({filepath})"
        if section:
            label += f" — {section}"
        text = r.get("text", "")[:600]
        lines.append(f"[{i}] **{label}**\n{text}")
    return "\n\n---\n\n".join(lines)


async def list_notes() -> str:
    """List all notes currently indexed in the notes collection."""
    try:
        client = get_client()
        result = await client.scroll(
            collection_name="notes",
            limit=1000,
            with_payload=["title", "filename", "filepath", "ingested_at"],
            with_vectors=False,
        )
    except Exception as e:
        return f"Failed to list notes: {e}"

    seen = {}
    for point in result[0]:
        p = point.payload
        key = p.get("filepath") or p.get("filename", "")
        if key not in seen:
            seen[key] = {
                "title": p.get("title") or key,
                "filepath": key,
                "ingested_at": (p.get("ingested_at") or "")[:10],
            }

    if not seen:
        return "No notes indexed. Use ingest_note or ask me to run vault re-index."

    lines = []
    for info in sorted(seen.values(), key=lambda x: x["filepath"]):
        lines.append(f"- **{info['title']}** ({info['filepath']})")
    return f"{len(seen)} note(s) indexed:\n" + "\n".join(lines)


async def list_knowledge_base() -> str:
    """List all documents/books currently ingested in the knowledge base."""
    try:
        client = get_client()
        result = await client.scroll(
            collection_name="sources",
            limit=1000,
            with_payload=["title", "filename", "source_type", "author", "ingested_at"],
            with_vectors=False,
        )
    except Exception as e:
        return f"Failed to list knowledge base: {e}"

    seen = {}
    for point in result[0]:
        p = point.payload
        key = p.get("filename", "")
        if key not in seen:
            seen[key] = {
                "title": p.get("title") or key,
                "author": p.get("author", ""),
                "source_type": p.get("source_type", ""),
                "ingested_at": (p.get("ingested_at") or "")[:10],
            }

    if not seen:
        return "Knowledge base is empty."

    lines = []
    for info in sorted(seen.values(), key=lambda x: x["ingested_at"], reverse=True):
        author = f" by {info['author']}" if info["author"] else ""
        lines.append(f"- **{info['title']}**{author} ({info['source_type']}, {info['ingested_at']})")
    return f"{len(seen)} document(s) in knowledge base:\n" + "\n".join(lines)


AUDIOBOOKBAY_URL = "https://audiobookbay.lu"
AUDIOBOOKBAY_COOKIE = "PHPSESSID=vrrrei24pldf9dj3ujgabtrof3"


async def _fetch_audiobook_detail(client: httpx.AsyncClient, url: str) -> dict:
    """Fetch a detail page and extract info hash, magnet link, and total size."""
    full_url = url if url.startswith("http") else f"{AUDIOBOOKBAY_URL}{url}"
    try:
        r = await client.get(
            full_url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Cookie": AUDIOBOOKBAY_COOKIE,
            },
            timeout=15,
        )
        html = r.text
    except Exception:
        return {}

    info_hash = ""
    h = re.search(r"Info Hash.*?<td>([0-9a-fA-F]{40})</td>", html, re.DOTALL)
    if h:
        info_hash = h.group(1).lower()

    magnet = ""
    if info_hash:
        dn = re.search(r"<title>([^<]+)</title>", html)
        name = dn.group(1).strip().replace(" ", "+") if dn else "audiobook"
        magnet = (
            f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
            "&tr=udp://tracker.openbittorrent.com:80"
            "&tr=udp://tracker.opentrackr.org:1337"
            "&tr=udp://open.stealth.si:80/announce"
        )

    sizes = re.findall(r"([\d.]+)\s*MBs", html)
    total_mb = sum(float(s) for s in sizes) if sizes else 0
    if not total_mb:
        sizes_gb = re.findall(r"([\d.]+)\s*GBs", html)
        total_mb = sum(float(s) * 1024 for s in sizes_gb)

    return {"magnet": magnet, "size_mb": round(total_mb, 1)}


async def search_audiobooks(query: str) -> str:
    """Search AudioBookBay for free audiobooks. Returns titles, authors, formats, magnet links, and sizes."""
    search_url = f"{AUDIOBOOKBAY_URL}/?s={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Cookie": AUDIOBOOKBAY_COOKIE,
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(search_url, headers=headers)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        return f"AudioBookBay search failed: {e}"

    # Split on post boundaries then extract fields from each slice
    post_slices = re.split(r'<div class="post"[^>]*>', html)[1:]
    if not post_slices:
        return f"No audiobooks found for '{query}'. Try different keywords."

    candidates = []
    for post in post_slices[:5]:
        title_m = re.search(r'<h2[^>]*><a href="([^"]+)"[^>]*>([^<]+)</a>', post)
        if not title_m:
            continue
        url, title = title_m.group(1), title_m.group(2).strip()
        author_m = re.search(r'Author[^:]*:\s*<[^>]+>([^<]+)', post, re.IGNORECASE)
        author = author_m.group(1).strip() if author_m else ""
        fmt_m = re.search(r'Format[^:]*:\s*<[^>]+>([^<]+)', post, re.IGNORECASE)
        fmt = fmt_m.group(1).strip() if fmt_m else ""
        candidates.append({"url": url, "title": title, "author": author, "fmt": fmt})

    if not candidates:
        return f"No audiobooks found for '{query}'. Try different keywords."

    async with httpx.AsyncClient(follow_redirects=True) as client:
        details = await asyncio.gather(*[_fetch_audiobook_detail(client, c["url"]) for c in candidates])

    results = []
    for c, d in zip(candidates, details):
        line = f"**{c['title']}**"
        if c["author"]:
            line += f" — {c['author']}"
        if c["fmt"]:
            line += f" [{c['fmt']}]"
        if d.get("size_mb"):
            size = d["size_mb"]
            line += f" | {size / 1024:.2f} GB" if size >= 1024 else f" | {size} MB"
        if d.get("magnet"):
            line += f"\nmagnet: `{d['magnet']}`"
        else:
            full_url = c["url"] if c["url"].startswith("http") else f"{AUDIOBOOKBAY_URL}{c['url']}"
            line += f"\npage: {full_url}"
        results.append(line)

    if not results:
        return f"No audiobooks found for '{query}'."
    return f"AudioBookBay results for '{query}':\n\n" + "\n\n".join(results)
