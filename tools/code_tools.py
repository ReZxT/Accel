import asyncio
import glob
import os
import subprocess
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


TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "bash": bash,
    "search_files": search_files,
    "list_dir": list_dir,
}

# irreversible by default — user can override in tool_settings
IRREVERSIBLE_TOOLS = {"bash", "write_file", "edit_file"}


async def execute_tool(name: str, args: dict) -> str:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        return await fn(**args)
    except TypeError as e:
        return f"Invalid arguments for {name}: {e}"
    except Exception as e:
        return f"Tool error ({name}): {e}"
