import asyncio
import hashlib
import os
import random
import string

import httpx
from circuit_breaker import breakers

ND_BASE = "http://localhost:4533/rest"
ND_AUTH = {"u": "ReZxT", "p": "Itakdalej5", "v": "1.16.1", "c": "accel", "f": "json"}
DBUS = "unix:path=/run/user/1000/bus"
PLAYER = "Feishin"

SC_API = "https://api-v2.soundcloud.com"
SC_USER_ID = "962917825"
SC_OAUTH = "2-314639-962917825-OTqTy9AV7Vig11"
SC_CLIENT_ID_CACHE = "/home/rezxt/.cache/yt-dlp/soundcloud/client_id.json"


def _sc_client_id() -> str:
    try:
        import json
        with open(SC_CLIENT_ID_CACHE) as f:
            return json.load(f)["data"]
    except Exception:
        return ""


def _sc_headers() -> dict:
    return {"Authorization": f"OAuth {SC_OAUTH}"}


def _params(**extra) -> dict:
    return {**ND_AUTH, **extra}


async def _get(endpoint: str, **kwargs) -> dict:
    cb = breakers["navidrome"]
    if not cb.can_execute():
        raise ConnectionError("Navidrome circuit is open")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{ND_BASE}/{endpoint}", params=_params(**kwargs), timeout=10)
            r.raise_for_status()
        data = r.json().get("subsonic-response", {})
        if data.get("status") != "ok":
            raise RuntimeError(data.get("error", {}).get("message", "Navidrome error"))
        cb.record_success()
        return data
    except Exception:
        cb.record_failure()
        raise


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
    except Exception as e:
        return f"playerctl error: {e}"


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


async def navidrome_search(query: str, type: str = "song", limit: int = 10) -> str:
    """Search the Navidrome music library for songs, albums, or artists."""
    try:
        data = await _get("search3", query=query, songCount=limit if type == "song" else 0,
                          albumCount=limit if type == "album" else 0,
                          artistCount=limit if type == "artist" else 0)
    except Exception as e:
        return f"Search failed: {e}"

    result = data.get("searchResult3", {})
    lines = []

    for song in result.get("song", []):
        dur = _fmt_duration(song.get("duration", 0))
        lines.append(f"[song:{song['id']}] **{song['title']}** — {song.get('artist', '?')} / {song.get('album', '?')} [{dur}]")
    for album in result.get("album", []):
        lines.append(f"[album:{album['id']}] **{album['name']}** — {album.get('artist', '?')} ({album.get('songCount', 0)} tracks)")
    for artist in result.get("artist", []):
        lines.append(f"[artist:{artist['id']}] **{artist['name']}** ({artist.get('albumCount', 0)} albums)")

    return "\n".join(lines) if lines else "No results found."


async def navidrome_get_playlists() -> str:
    """List all playlists in Navidrome."""
    try:
        data = await _get("getPlaylists")
    except Exception as e:
        return f"Failed: {e}"
    playlists = data.get("playlists", {}).get("playlist", [])
    if not playlists:
        return "No playlists found."
    lines = [f"[{p['id']}] **{p['name']}** — {p.get('songCount', 0)} tracks, {_fmt_duration(p.get('duration', 0))}" for p in playlists]
    return "\n".join(lines)


async def navidrome_get_playlist(playlist_id: str) -> str:
    """Get tracks in a Navidrome playlist."""
    try:
        data = await _get("getPlaylist", id=playlist_id)
    except Exception as e:
        return f"Failed: {e}"
    pl = data.get("playlist", {})
    songs = pl.get("entry", [])
    header = f"**{pl.get('name', playlist_id)}** — {len(songs)} tracks\n"
    lines = [f"{i+1}. [song:{s['id']}] {s['title']} — {s.get('artist', '?')} [{_fmt_duration(s.get('duration', 0))}]"
             for i, s in enumerate(songs)]
    return header + "\n".join(lines) if lines else header + "Empty playlist."


async def navidrome_create_playlist(name: str, song_ids: list[str] = None) -> str:
    """Create a new Navidrome playlist, optionally pre-populated with song IDs."""
    try:
        existing = await _get("getPlaylists")
        for p in existing.get("playlists", {}).get("playlist", []):
            if p.get("name", "").lower() == name.lower():
                return f"Playlist **{p['name']}** already exists (id: {p['id']}). No duplicate created."
    except Exception:
        pass
    try:
        if song_ids:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{ND_BASE}/createPlaylist",
                                     params={**ND_AUTH, "name": name, "songId": song_ids},
                                     timeout=10)
                r.raise_for_status()
                data = r.json().get("subsonic-response", {})
        else:
            data = await _get("createPlaylist", name=name)
    except Exception as e:
        return f"Failed to create playlist: {e}"
    pl = data.get("playlist", {})
    return f"Created playlist **{pl.get('name', name)}** (id: {pl.get('id', '?')})"


async def navidrome_update_playlist(playlist_id: str, add_song_ids: list[str] = None,
                                     remove_song_indices: list[int] = None,
                                     name: str = "") -> str:
    """Add or remove tracks from a Navidrome playlist. Use navidrome_get_playlist first to see current track indices."""
    try:
        params_extra: dict = {"playlistId": playlist_id}
        if name:
            params_extra["name"] = name
        async with httpx.AsyncClient() as client:
            p = {**ND_AUTH, **params_extra}
            if add_song_ids:
                p["songIdToAdd"] = add_song_ids
            if remove_song_indices:
                p["songIndexToRemove"] = remove_song_indices
            r = await client.get(f"{ND_BASE}/updatePlaylist", params=p, timeout=10)
            r.raise_for_status()
    except Exception as e:
        return f"Failed to update playlist: {e}"
    return f"Playlist {playlist_id} updated."


async def navidrome_delete_playlist(playlist_id: str) -> str:
    """Delete a Navidrome playlist by ID."""
    try:
        await _get("deletePlaylist", id=playlist_id)
    except Exception as e:
        return f"Failed to delete playlist: {e}"
    return f"Playlist {playlist_id} deleted."


async def player_control(action: str, value: float = 0.0) -> str:
    """Control Feishin playback. Actions: play, pause, play_pause, next, previous, seek (value=seconds), volume (value=0.0-1.0)."""
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
        return f"Unknown action '{action}'. Valid: play, pause, play_pause, next, previous, seek, volume."
    result = await _playerctl(*cmd)
    return f"Player: {action}" + (f" → {result}" if result and "error" in result else "")


async def player_load(song_ids: list[str]) -> dict:
    """Load one or more songs into the Accel in-browser player by Navidrome song ID. Use navidrome_search first to get IDs."""
    tracks = []
    for sid in song_ids[:50]:
        try:
            data = await _get("getSong", id=sid)
            song = data.get("song", {})
            tracks.append({
                "id": sid,
                "title": song.get("title", "Unknown"),
                "artist": song.get("artist", "") or song.get("albumArtist", ""),
                "album": song.get("album", ""),
                "duration": song.get("duration", 0),
                "stream_url": f"/navidrome/rest/stream?id={sid}&u=ReZxT&p=Itakdalej5&v=1.16.1&c=accel&format=opus",
                "art_url": f"/navidrome/rest/getCoverArt?id={sid}&u=ReZxT&p=Itakdalej5&v=1.16.1&c=accel&size=300",
            })
        except Exception:
            continue
    if not tracks:
        return {"__type": "error", "text": "No tracks found for those IDs."}
    return {"__type": "play_queue", "tracks": tracks}


async def player_now_playing() -> str:
    """Get the currently playing track in Feishin with status and position."""
    status, position, meta_raw = await asyncio.gather(
        _playerctl("status"),
        _playerctl("position"),
        _playerctl("metadata"),
    )
    if not status or "error" in status:
        return "No player detected or nothing playing."

    meta: dict = {}
    for line in meta_raw.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            meta[parts[1]] = parts[2]

    title = meta.get("xesam:title", "Unknown")
    artist = meta.get("xesam:artist", "") or meta.get("xesam:albumArtist", "")
    album = meta.get("xesam:album", "")
    length_us = int(meta.get("mpris:length", 0))
    length_s = length_us / 1_000_000
    try:
        pos_s = float(position)
    except (ValueError, TypeError):
        pos_s = 0.0

    return (f"**{title}** — {artist}\n"
            f"Album: {album}\n"
            f"Status: {status} | Position: {_fmt_duration(pos_s)} / {_fmt_duration(length_s)}")


async def soundcloud_get_playlists() -> str:
    """List all SoundCloud playlists (public and private) from the logged-in account."""
    cid = _sc_client_id()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SC_API}/users/{SC_USER_ID}/playlists",
                params={"limit": 100, "client_id": cid},
                headers=_sc_headers(),
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"SoundCloud API error: {e}"

    playlists = data.get("collection", [])
    if not playlists:
        return "No playlists found."
    lines = []
    for p in playlists:
        vis = "🔒" if p.get("sharing") == "private" else "🌐"
        lines.append(f"{vis} [{p['id']}] **{p['title']}** — {p.get('track_count', 0)} tracks")
    return "\n".join(lines)


async def soundcloud_get_playlist(playlist_id: str) -> str:
    """Get tracks in a SoundCloud playlist by ID. Use soundcloud_get_playlists first to find IDs."""
    cid = _sc_client_id()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SC_API}/playlists/{playlist_id}",
                params={"client_id": cid},
                headers=_sc_headers(),
                timeout=10,
            )
            r.raise_for_status()
            pl = r.json()
    except Exception as e:
        return f"SoundCloud API error: {e}"

    tracks = pl.get("tracks", [])

    # SoundCloud only returns full data for the first 5 tracks; rest are stubs with just id/kind
    stub_ids = [str(t["id"]) for t in tracks if "title" not in t]
    if stub_ids:
        try:
            async with httpx.AsyncClient() as client:
                # Batch fetch in chunks of 50
                full: dict[int, dict] = {}
                for i in range(0, len(stub_ids), 50):
                    chunk = stub_ids[i:i+50]
                    r = await client.get(
                        f"{SC_API}/tracks",
                        params={"ids": ",".join(chunk), "client_id": cid},
                        headers=_sc_headers(),
                        timeout=15,
                    )
                    if r.status_code == 200:
                        for t in r.json():
                            full[t["id"]] = t
            tracks = [full.get(t["id"], t) for t in tracks]
        except Exception:
            pass  # use whatever data we have

    header = f"**{pl.get('title', playlist_id)}** — {len(tracks)} tracks\n"
    lines = []
    for i, t in enumerate(tracks):
        dur = _fmt_duration((t.get("duration") or 0) / 1000)
        title = t.get("title") or f"[id:{t.get('id')}]"
        artist = t.get("user", {}).get("username", "?") if isinstance(t.get("user"), dict) else "?"
        lines.append(f"{i+1}. **{title}** — {artist} [{dur}]")
    return header + "\n".join(lines) if lines else header + "Empty playlist."
