import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)

STATS_PATH = Path("~/.config/accel/tool_stats.json").expanduser()
FLUSH_INTERVAL = 120  # seconds


class ToolStats:
    def __init__(self):
        self.usage_counts: dict[str, int] = {}
        self.last_used: dict[str, float] = {}
        self.cooccurrence: dict[str, dict[str, int]] = {}
        self._session_tools: dict[str, set[str]] = {}
        self._dirty = False
        self._last_flush = time.time()

    @classmethod
    def load(cls) -> "ToolStats":
        ts = cls()
        if STATS_PATH.exists():
            try:
                data = json.loads(STATS_PATH.read_text())
                ts.usage_counts = data.get("usage_counts", {})
                ts.last_used = data.get("last_used", {})
                ts.cooccurrence = data.get("cooccurrence", {})
            except Exception as e:
                log.warning("Failed to load tool stats: %s", e)
        return ts

    def record_call(self, tool_name: str, session_id: str) -> None:
        self.usage_counts[tool_name] = self.usage_counts.get(tool_name, 0) + 1
        self.last_used[tool_name] = time.time()
        self._session_tools.setdefault(session_id, set()).add(tool_name)
        self._dirty = True
        self._maybe_flush()

    def record_session_end(self, session_id: str) -> None:
        tools = self._session_tools.pop(session_id, set())
        if len(tools) < 2:
            return
        tool_list = sorted(tools)
        for i, a in enumerate(tool_list):
            for b in tool_list[i + 1:]:
                self.cooccurrence.setdefault(a, {})[b] = self.cooccurrence.get(a, {}).get(b, 0) + 1
                self.cooccurrence.setdefault(b, {})[a] = self.cooccurrence.get(b, {}).get(a, 0) + 1
        self._dirty = True
        self._persist()

    def get_cooccurrence_boost(self, tool_name: str, session_id: str) -> float:
        session_tools = self._session_tools.get(session_id, set())
        if not session_tools or tool_name not in self.cooccurrence:
            return 0.0
        co = self.cooccurrence[tool_name]
        total = sum(co.get(t, 0) for t in session_tools)
        return min(0.10, total / 10.0)

    def get_recency_score(self, tool_name: str) -> float:
        ts = self.last_used.get(tool_name, 0)
        if not ts:
            return 0.0
        days = (time.time() - ts) / 86400
        return 1 / (1 + days * 0.05)

    def _maybe_flush(self) -> None:
        if self._dirty and time.time() - self._last_flush > FLUSH_INTERVAL:
            self._persist()

    def _persist(self) -> None:
        try:
            STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = STATS_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "usage_counts": self.usage_counts,
                "last_used": self.last_used,
                "cooccurrence": self.cooccurrence,
            }, indent=2))
            os.replace(tmp, STATS_PATH)
            self._dirty = False
            self._last_flush = time.time()
        except Exception as e:
            log.warning("Failed to persist tool stats: %s", e)


tool_stats = ToolStats.load()
