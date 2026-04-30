import logging
import httpx
from config import config
from circuit_breaker import breakers

log = logging.getLogger(__name__)

_profile_cache: dict | None = None

DEFAULT_TOOL_SETTINGS = {
    "read_file": "auto",
    "write_file": "require",
    "edit_file": "require",
    "bash": "require",
    "search_files": "auto",
    "list_dir": "auto",
}


async def get_profile(force_refresh: bool = False) -> dict:
    global _profile_cache
    if _profile_cache and not force_refresh:
        return _profile_cache
    cb = breakers["splitter"]
    if not cb.can_execute():
        return _profile_cache or {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{config.code_splitter_url}/profile")
            if r.status_code == 200:
                _profile_cache = r.json()
                cb.record_success()
                return _profile_cache
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        log.warning("get_profile failed: %s", e)
    return _profile_cache or {}


async def get_tool_settings() -> dict:
    profile = await get_profile()
    return profile.get("tool_settings", DEFAULT_TOOL_SETTINGS)


async def save_tool_settings(settings: dict) -> None:
    global _profile_cache
    profile = await get_profile()
    profile["tool_settings"] = settings
    _profile_cache = profile
    cb = breakers["splitter"]
    if not cb.can_execute():
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.put(f"{config.code_splitter_url}/profile", json=profile)
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        log.warning("save_tool_settings failed: %s", e)
