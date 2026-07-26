"""A tiny in-process TTL cache.

One FastAPI instance, one process, no Redis — a dict with a timestamp is the honest amount
of caching machinery for a single-instance academic deployment (ADR-0004's reasoning applied
to caching, not just storage).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    def __init__(self, ttl_s: int):
        self.ttl_s = ttl_s
        self._store: dict[Any, tuple[float, Any]] = {}

    def get_or_set(self, key: Any, compute: Callable[[], Any]) -> Any:
        now = time.time()
        cached = self._store.get(key)
        if cached is not None and now - cached[0] < self.ttl_s:
            return cached[1]
        value = compute()
        self._store[key] = (now, value)
        return value
