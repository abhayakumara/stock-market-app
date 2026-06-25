"""Lightweight in-process metrics (no external dependency).

Good enough for a single-user app: counters surfaced at ``GET /metrics``. Swap for
Prometheus/OpenTelemetry when this grows multi-process.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class Metrics:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self._started = time.monotonic()

    def inc(self, name: str, n: int = 1) -> None:
        with self._lock:
            self._counters[name] += n

    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
        return {"uptime_seconds": round(time.monotonic() - self._started, 1), "counters": counters}
