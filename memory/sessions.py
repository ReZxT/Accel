import httpx
from config import config


async def load_session(session_id: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{config.code_splitter_url}/session",
                params={"session_id": session_id},
            )
            if r.status_code == 200:
                return r.json().get("messages", [])
    except Exception:
        pass
    return []


async def save_session(session_id: str, messages: list[dict]) -> None:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.put(
                f"{config.code_splitter_url}/session",
                json={"session_id": session_id, "messages": messages},
            )
    except Exception:
        pass
