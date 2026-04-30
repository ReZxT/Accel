import logging
import httpx
from config import config
from circuit_breaker import breakers

log = logging.getLogger(__name__)


async def load_session(session_id: str) -> list[dict]:
    cb = breakers["splitter"]
    if not cb.can_execute():
        log.warning("Splitter circuit open — returning empty session")
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{config.code_splitter_url}/session",
                params={"session_id": session_id},
            )
            if r.status_code == 200:
                cb.record_success()
                return r.json().get("messages", [])
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        log.warning("load_session failed: %s", e)
    return []


async def save_session(session_id: str, messages: list[dict]) -> None:
    cb = breakers["splitter"]
    if not cb.can_execute():
        return
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.put(
                f"{config.code_splitter_url}/session",
                json={"session_id": session_id, "messages": messages},
            )
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        log.warning("save_session failed: %s", e)
