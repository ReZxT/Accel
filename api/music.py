import asyncio
import os
import re

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/music", tags=["music"])

DBUS = "unix:path=/run/user/1000/bus"
PLAYER = "Feishin"

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

ND_BASE = os.getenv("NAVIDROME_URL", "http://localhost:4533/rest")
ND_USER = os.getenv("NAVIDROME_USER", "")
ND_PASS = os.getenv("NAVIDROME_PASSWORD", "")
ND_AUTH = {"u": ND_USER, "p": ND_PASS, "v": "1.16.1", "c": "accel", "f": "json"}


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


async def _nd_get(endpoint: str, **params) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{ND_BASE}/{endpoint}", params={**ND_AUTH, **params})
        data = r.json().get("subsonic-response", {})
        return data


def _song_to_track(s: dict) -> dict:
    sid = s.get("id", "")
    cover = s.get("coverArt", sid)
    return {
        "id": sid,
        "title": s.get("title", ""),
        "artist": s.get("artist", ""),
        "album": s.get("album", ""),
        "duration": s.get("duration", 0),
        "stream_url": f"/navidrome/rest/stream?id={sid}&{_nd_qs()}",
        "art_url": f"/navidrome/rest/getCoverArt?id={cover}&size=300&{_nd_qs()}" if cover else "",
    }


def _nd_qs() -> str:
    from urllib.parse import urlencode
    return urlencode(ND_AUTH)


@router.get("/library")
async def library(query: str = "", offset: int = 0, count: int = 50):
    data = await _nd_get(
        "search3",
        query=query or "",
        songCount=str(count),
        songOffset=str(offset),
        albumCount="0",
        artistCount="0",
    )
    songs = data.get("searchResult3", {}).get("song", [])
    return {"tracks": [_song_to_track(s) for s in songs]}


@router.get("/playlists")
async def playlists():
    data = await _nd_get("getPlaylists")
    pls = data.get("playlists", {}).get("playlist", [])
    return {"playlists": [{"id": p["id"], "name": p["name"], "songCount": p.get("songCount", 0), "duration": p.get("duration", 0)} for p in pls]}


@router.get("/playlist/{playlist_id}")
async def playlist_tracks(playlist_id: str):
    data = await _nd_get("getPlaylist", id=playlist_id)
    pl = data.get("playlist", {})
    songs = pl.get("entry", [])
    return {
        "id": pl.get("id", ""),
        "name": pl.get("name", ""),
        "tracks": [_song_to_track(s) for s in songs],
    }


@router.get("/random")
async def random_songs(count: int = 50):
    data = await _nd_get("getRandomSongs", size=str(count))
    songs = data.get("randomSongs", {}).get("song", [])
    return {"tracks": [_song_to_track(s) for s in songs]}


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
