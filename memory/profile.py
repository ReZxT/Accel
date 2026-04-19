import httpx
from config import config

_profile_cache: dict | None = None


async def get_profile(force_refresh: bool = False) -> dict:
    global _profile_cache
    if _profile_cache and not force_refresh:
        return _profile_cache
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{config.code_splitter_url}/profile")
            if r.status_code == 200:
                _profile_cache = r.json()
                return _profile_cache
    except Exception:
        pass
    return {}
