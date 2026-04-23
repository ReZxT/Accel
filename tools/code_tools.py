import asyncio
import glob
import os
import shutil
import stat
import subprocess
from datetime import datetime
from pathlib import Path

from config import config

WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", str(Path.home()))
MAX_OUTPUT = 10_000  # chars


def _resolve(path: str) -> str:
    """Resolve path, absolute or relative to workspace root."""
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(Path(WORKSPACE_ROOT) / p)


async def read_file(path: str, offset: int = 0, limit: int = 200) -> str:
    resolved = _resolve(path)
    try:
        with open(resolved, "r", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        slice_ = lines[offset: offset + limit]
        result = "".join(f"{offset + i + 1}\t{l}" for i, l in enumerate(slice_))
        if total > offset + limit:
            result += f"\n... ({total - offset - limit} more lines, use offset/limit to read more)"
        return result
    except Exception as e:
        return f"Error reading {path}: {e}"


async def write_file(path: str, content: str) -> str:
    resolved = _resolve(path)
    try:
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w") as f:
            f.write(content)
        lines = content.count("\n") + 1
        return f"Written {lines} lines to {resolved}"
    except Exception as e:
        return f"Error writing {path}: {e}"


async def edit_file(path: str, old_content: str, new_content: str) -> str:
    resolved = _resolve(path)
    try:
        with open(resolved, "r", errors="replace") as f:
            text = f.read()
        if old_content not in text:
            return f"Error: old_content not found in {path}. No changes made."
        if text.count(old_content) > 1:
            return f"Error: old_content matches {text.count(old_content)} locations in {path}. Make it more specific."
        new_text = text.replace(old_content, new_content, 1)
        with open(resolved, "w") as f:
            f.write(new_text)
        return f"Edited {resolved} successfully."
    except Exception as e:
        return f"Error editing {path}: {e}"


async def bash(command: str, timeout: int = 30) -> str:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=WORKSPACE_ROOT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"Command timed out after {timeout}s"
        output = stdout.decode(errors="replace")
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + f"\n... (truncated, {len(output) - MAX_OUTPUT} more chars)"
        exit_code = proc.returncode
        if exit_code != 0:
            return f"Exit code {exit_code}:\n{output}"
        return output or "(no output)"
    except Exception as e:
        return f"Error running command: {e}"


async def search_files(pattern: str, path: str = ".", search_type: str = "content") -> str:
    resolved = _resolve(path)
    try:
        if search_type == "name":
            matches = []
            for root, dirs, files in os.walk(resolved):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    if glob.fnmatch.fnmatch(f, pattern):
                        matches.append(os.path.join(root, f))
            if not matches:
                return "No files found."
            return "\n".join(matches[:200])
        else:
            proc = await asyncio.create_subprocess_exec(
                "rg", "--line-number", "--max-count", "5",
                "--glob", "!.git", pattern, resolved,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode(errors="replace")
            if not output.strip():
                return "No matches found."
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n... (truncated)"
            return output
    except Exception as e:
        return f"Error searching: {e}"


async def list_dir(path: str) -> str:
    resolved = _resolve(path)
    try:
        entries = sorted(os.scandir(resolved), key=lambda e: (not e.is_dir(), e.name))
        lines = []
        for e in entries:
            if e.name.startswith("."):
                continue
            if e.is_dir():
                lines.append(f"  {e.name}/")
            else:
                size = e.stat().st_size
                size_str = f"{size:,}" if size < 1_000_000 else f"{size // 1024:,}K"
                lines.append(f"  {e.name}  ({size_str} bytes)")
        return f"{resolved}:\n" + "\n".join(lines) if lines else f"{resolved}: (empty)"
    except Exception as e:
        return f"Error listing {path}: {e}"


_PROTECTED = {".git", ".env", ".ssh", ".gnupg"}


def _safety_check(path: str, operation: str) -> str | None:
    """Return error string if the path is unsafe for the given operation, else None."""
    p = Path(_resolve(path))
    if any(part in _PROTECTED for part in p.parts):
        return f"Refused: '{path}' is inside a protected path ({_PROTECTED})"
    if p == Path(WORKSPACE_ROOT):
        return f"Refused: cannot {operation} the workspace root"
    return None


async def delete_file(path: str) -> str:
    """Delete a single file. Refuses to delete directories, protected paths (.git, .env, .ssh), or the workspace root."""
    resolved = _resolve(path)
    p = Path(resolved)
    err = _safety_check(path, "delete")
    if err:
        return err
    if not p.exists():
        return f"Not found: {resolved}"
    if p.is_dir():
        return f"Refused: '{resolved}' is a directory. Use bash to remove directories."
    try:
        p.unlink()
        return f"Deleted: {resolved}"
    except Exception as e:
        return f"Error deleting {resolved}: {e}"


async def get_file_info(path: str) -> str:
    """Get detailed info about a file or directory: size, permissions, owner, timestamps."""
    resolved = _resolve(path)
    p = Path(resolved)
    if not p.exists():
        return f"Not found: {resolved}"
    try:
        st = p.stat()
        mode = stat.filemode(st.st_mode)
        size = st.st_size
        size_str = (
            f"{size} B" if size < 1024
            else f"{size / 1024:.1f} KB" if size < 1024 ** 2
            else f"{size / 1024 ** 2:.1f} MB"
        )
        try:
            import pwd, grp
            owner = pwd.getpwuid(st.st_uid).pw_name
            group = grp.getgrgid(st.st_gid).gr_name
        except Exception:
            owner, group = str(st.st_uid), str(st.st_gid)
        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        ctime = datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        atime = datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S")
        kind = "directory" if p.is_dir() else ("symlink" if p.is_symlink() else "file")
        lines = [
            f"Path:        {resolved}",
            f"Type:        {kind}",
            f"Size:        {size_str} ({size:,} bytes)",
            f"Permissions: {mode}",
            f"Owner:       {owner}:{group}",
            f"Modified:    {mtime}",
            f"Created:     {ctime}",
            f"Accessed:    {atime}",
        ]
        if p.is_symlink():
            lines.append(f"Target:      {os.readlink(resolved)}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting info for {resolved}: {e}"


async def move_file(source: str, destination: str, overwrite: bool = False) -> str:
    """Move or rename a file or directory. Refuses to overwrite existing paths unless overwrite=True.
    Also refuses to touch protected paths (.git, .env, .ssh)."""
    src = _resolve(source)
    dst = _resolve(destination)
    for path, label in ((source, "source"), (destination, "destination")):
        err = _safety_check(path, "move")
        if err:
            return err
    src_p = Path(src)
    dst_p = Path(dst)
    if not src_p.exists():
        return f"Not found: {src}"
    if dst_p.exists() and not overwrite:
        return f"Refused: destination '{dst}' already exists. Pass overwrite=true to replace it."
    try:
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return f"Moved: {src} → {dst}"
    except Exception as e:
        return f"Error moving {src} → {dst}: {e}"


SPLITTER_URL = os.getenv("SPLITTER_URL", "http://localhost:9200")

BOOKS_DIR = "/mnt/WD/Books"
AUDIOBOOKS_DIR = "/mnt/WD/Audiobooks"
DOCUMENTS_DIR = "/mnt/WD/Documents"


async def ingest_note(path: str, title: str = "") -> str:
    """Ingest or re-ingest a local markdown note into the notes knowledge base."""
    import httpx
    resolved = _resolve(path)
    p = Path(resolved)
    if not p.exists():
        return f"File not found: {resolved}"
    if not p.is_file():
        return f"Not a file: {resolved}"
    try:
        content = p.read_text(errors="replace")
    except Exception as e:
        return f"Error reading {resolved}: {e}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{SPLITTER_URL}/ingest/note",
                json={
                    "content": content,
                    "filename": p.name,
                    "filepath": str(p),
                    "title": title or p.stem,
                },
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return f"Ingest note failed: {e}"
    if data.get("status") == "ok":
        return f"Ingested note '{data.get('title', p.stem)}' — {data.get('chunks_stored', 0)} chunks stored."
    return f"Ingest note error: {data.get('error', 'unknown')}"


async def add_torrent(magnet: str) -> str:
    """Open a magnet link in the system torrent client via xdg-open."""
    if not magnet.startswith("magnet:"):
        return "Invalid magnet link — must start with 'magnet:'"
    try:
        proc = await asyncio.create_subprocess_exec(
            "xdg-open", magnet,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            return f"xdg-open failed (exit {proc.returncode}): {stderr.decode().strip()}"
        return "Magnet link sent to torrent client."
    except Exception as e:
        return f"Failed to open magnet link: {e}"

_SOURCE_TYPE_BY_FOLDER = {
    "books": "book",
    "audiobooks": None,  # not ingestible
    "documents": "document",
}


async def ingest_file(path: str = "", file_path: str = "", filepath: str = "", title: str = "", author: str = "", source_type: str = "", **kwargs) -> str:
    path = path or file_path or filepath
    if not path:
        return f"Error: ingest_file requires a 'path' argument. Received: {dict(**kwargs)}"
    """Ingest a local document (PDF, EPUB, TXT, MD, RST) into the knowledge base (Qdrant sources)."""
    import asyncio
    import base64
    import httpx

    resolved = _resolve(path)
    p = Path(resolved)
    if not p.exists():
        return f"File not found: {resolved}"
    if not p.is_file():
        return f"Not a file: {resolved}"

    ext = p.suffix.lower().lstrip(".")
    if ext not in ("pdf", "epub", "txt", "md", "rst"):
        return f"Unsupported file type: .{ext} — supported: pdf, epub, txt, md, rst"

    if not source_type:
        folder = p.parent.name.lower()
        source_type = _SOURCE_TYPE_BY_FOLDER.get(folder, "document")
        if source_type is None:
            return "Audio files cannot be ingested into the knowledge base."
        if ext == "epub" and source_type == "document":
            source_type = "book"

    size_mb = p.stat().st_size / 1024 / 1024
    with open(resolved, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{SPLITTER_URL}/ingest",
                json={
                    "base64": b64,
                    "filename": p.name,
                    "source_type": source_type,
                    "title": title or p.stem,
                    "author": author or "",
                },
                timeout=30,
            )
            r.raise_for_status()
            job_id = r.json()["job_id"]
        except Exception as e:
            return f"Failed to start ingest: {e}"

    # Poll until done
    while True:
        await asyncio.sleep(3)
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{SPLITTER_URL}/ingest/status/{job_id}", timeout=10)
                status = r.json()
        except Exception as e:
            return f"Poll failed: {e}"

        if status["status"] == "done":
            chunks = status.get("chunks_stored", 0)
            label = title or p.stem
            return f"Ingested '{label}' ({size_mb:.1f} MB, {source_type}) — {chunks} chunks stored."
        elif status["status"] == "error":
            return f"Ingest failed: {status.get('error', 'unknown error')}"


from tools.web_tools import search_web, fetch_url, screenshot_url, search_knowledge_base, list_knowledge_base, search_notes, list_notes, search_audiobooks, save_memory, update_memory, delete_memory, search_facts, search_procedures, search_episodes, download_file, delete_source, delete_note
from tools.calculator import calculate
from tools.calendar_tools import calendar_add_event, calendar_get_events, calendar_delete_event, calendar_today
from tools.converter import convert_units, convert_currency

TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "bash": bash,
    "search_files": search_files,
    "list_dir": list_dir,
    "download_file": download_file,
    "search_web": search_web,
    "search_audiobooks": search_audiobooks,
    "fetch_url": fetch_url,
    "search_knowledge_base": search_knowledge_base,
    "list_knowledge_base": list_knowledge_base,
    "search_notes": search_notes,
    "list_notes": list_notes,
    "ingest_note": ingest_note,
    "save_memory": save_memory,
    "update_memory": update_memory,
    "delete_memory": delete_memory,
    "search_facts": search_facts,
    "search_procedures": search_procedures,
    "search_episodes": search_episodes,
    "screenshot_url": screenshot_url,
    "delete_file": delete_file,
    "get_file_info": get_file_info,
    "move_file": move_file,
    "add_torrent": add_torrent,
    "ingest_file": ingest_file,
    "delete_source": delete_source,
    "delete_note": delete_note,
    "calculate": calculate,
    "calendar_add_event": calendar_add_event,
    "calendar_get_events": calendar_get_events,
    "calendar_delete_event": calendar_delete_event,
    "calendar_today": calendar_today,
    "convert_units": convert_units,
    "convert_currency": convert_currency,
}

# irreversible by default — user can override in tool_settings
IRREVERSIBLE_TOOLS = {"bash", "write_file", "edit_file", "delete_file", "move_file", "ingest_file", "ingest_note", "add_torrent", "calendar_add_event", "calendar_delete_event", "delete_source", "delete_note", "delete_memory"}


async def execute_tool(name: str, args: dict) -> str | dict:
    """Execute a tool. Returns str for text results, dict for image results."""
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        return await fn(**args)
    except TypeError as e:
        return f"Invalid arguments for {name}: {e} (got: {list(args.keys())})"
    except Exception as e:
        return f"Tool error ({name}): {e}"
