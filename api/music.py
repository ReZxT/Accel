import asyncio
import os
import re

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/music", tags=["music"])

DBUS = "unix:path=/run/user/1000/bus"
PLAYER = "Feishin"

ND_BASE = "http://localhost:4533/rest"
ND_AUTH = {"u": "ReZxT", "p": "Itakdalej5", "v": "1.16.1", "c": "accel", "f": "json"}


async def _playerctl(*args: str) -> str:
    env = {**os.environ, "DBUS_SESSION_BUS_ADDRESS": DBUS}
    try:
        proc = await asyncio.create_subprocess_exec(
            "playerctl", "-p", PLAYER, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        return stdout.decode().strip()
    except Exception:
        return ""


@router.get("/now_playing")
async def now_playing():
    status, position, meta_raw = await asyncio.gather(
        _playerctl("status"),
        _playerctl("position"),
        _playerctl("metadata"),
    )

    if not status:
        return {"status": "stopped"}

    meta: dict[str, str] = {}
    for line in meta_raw.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            meta[parts[1]] = parts[2]

    length_us = int(meta.get("mpris:length", 0))
    art_url = meta.get("mpris:artUrl", "")

    # Rewrite art URL to go through our proxy so browser avoids CORS
    art_proxy = ""
    if art_url.startswith("http://localhost:4533"):
        art_proxy = "/navidrome" + art_url[len("http://localhost:4533"):]

    try:
        pos_sec = float(position)
    except (ValueError, TypeError):
        pos_sec = 0.0

    return {
        "status": status.lower(),
        "title": meta.get("xesam:title", ""),
        "artist": meta.get("xesam:artist", "") or meta.get("xesam:albumArtist", ""),
        "album": meta.get("xesam:album", ""),
        "length": length_us / 1_000_000,
        "position": pos_sec,
        "art_url": art_proxy,
    }


@router.post("/control")
async def control(action: str, value: float = 0.0):
    cmd_map = {
        "play":       ["play"],
        "pause":      ["pause"],
        "play_pause": ["play-pause"],
        "next":       ["next"],
        "previous":   ["previous"],
        "seek":       ["position", str(value)],
        "volume":     ["volume", str(max(0.0, min(1.0, value)))],
    }
    cmd = cmd_map.get(action)
    if not cmd:
        return {"error": f"Unknown action: {action}"}
    await _playerctl(*cmd)
    return {"ok": True, "action": action}
