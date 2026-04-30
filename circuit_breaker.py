import asyncio
import time
import logging

log = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: float = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"
        self.last_failure_time: float = 0

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                log.info("[CB:%s] half-open — testing", self.name)
                return True
            return False
        # half-open: allow one request through
        return True

    def record_success(self):
        if self.state != "closed":
            log.info("[CB:%s] closed — recovered", self.name)
        self.failures = 0
        self.state = "closed"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == "half-open" or self.failures >= self.failure_threshold:
            self.state = "open"
            log.warning("[CB:%s] open — %d failures, backing off %ds", self.name, self.failures, self.reset_timeout)

    @property
    def is_open(self) -> bool:
        return self.state == "open" and time.time() - self.last_failure_time <= self.reset_timeout

    def status(self) -> dict:
        return {"name": self.name, "state": self.state, "failures": self.failures}


async def protected_call(breaker: CircuitBreaker, coro, fallback=None):
    if not breaker.can_execute():
        log.warning("[CB:%s] open — using fallback", breaker.name)
        if fallback is not None:
            return fallback() if callable(fallback) else fallback
        raise ConnectionError(f"{breaker.name} circuit is open")
    try:
        result = await coro
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure()
        if fallback is not None:
            log.warning("[CB:%s] failed (%s) — using fallback", breaker.name, e)
            return fallback() if callable(fallback) else fallback
        raise


# -- singleton breakers for each service domain --

breakers = {
    "chat":       CircuitBreaker("chat",       failure_threshold=2, reset_timeout=30),
    "curator":    CircuitBreaker("curator",     failure_threshold=3, reset_timeout=60),
    "embeddings": CircuitBreaker("embeddings",  failure_threshold=3, reset_timeout=60),
    "qdrant":     CircuitBreaker("qdrant",      failure_threshold=3, reset_timeout=30),
    "searxng":    CircuitBreaker("searxng",     failure_threshold=3, reset_timeout=120),
    "navidrome":  CircuitBreaker("navidrome",   failure_threshold=3, reset_timeout=120),
    "splitter":   CircuitBreaker("splitter",    failure_threshold=3, reset_timeout=60),
    "playwright": CircuitBreaker("playwright",  failure_threshold=2, reset_timeout=120),
}


def all_status() -> list[dict]:
    return [b.status() for b in breakers.values()]
