import asyncio
from typing import Any

# pending[request_id] = (event, result_container)
_pending: dict[str, tuple[asyncio.Event, list]] = {}

APPROVAL_TIMEOUT = 300  # 5 minutes


def register(request_id: str) -> asyncio.Event:
    event = asyncio.Event()
    _pending[request_id] = (event, [None])
    return event


async def wait_for_approval(request_id: str) -> bool:
    if request_id not in _pending:
        return False
    event, result = _pending[request_id]
    try:
        await asyncio.wait_for(event.wait(), timeout=APPROVAL_TIMEOUT)
        return bool(result[0])
    except asyncio.TimeoutError:
        return False
    finally:
        _pending.pop(request_id, None)


def resolve(request_id: str, approved: bool) -> bool:
    if request_id not in _pending:
        return False
    event, result = _pending[request_id]
    result[0] = approved
    event.set()
    return True
