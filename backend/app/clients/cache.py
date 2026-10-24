"""In-memory cache in front of a data source.

Keys are the exact request ranges; the decision time is never part of a key, so moving the cutoff
for the same delivery day is always served from cache. Concurrent requests for the same key wait
for a single upstream call instead of each making their own.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import date, datetime

from app.clients.base import DataSource, SourceResult

MAX_ENTRIES = 256


class CachedSource:
    def __init__(self, source: DataSource, ttl_seconds: float) -> None:
        self._source = source
        self._ttl = ttl_seconds
        self._entries: dict[tuple[object, ...], tuple[float, SourceResult]] = {}
        self._locks: dict[tuple[object, ...], asyncio.Lock] = {}

    async def fetch_actuals(self, first: date, last: date) -> SourceResult:
        return await self._cached(
            ("FUELHH", first, last), lambda: self._source.fetch_actuals(first, last)
        )

    async def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> SourceResult:
        return await self._cached(
            ("WINDFOR", published_from, published_to),
            lambda: self._source.fetch_forecasts(published_from, published_to),
        )

    async def _cached(
        self, key: tuple[object, ...], load: Callable[[], Awaitable[SourceResult]]
    ) -> SourceResult:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            entry = self._entries.get(key)
            if entry and time.monotonic() - entry[0] < self._ttl:
                return replace(entry[1], cache="HIT")
            result = await load()
            self._entries[key] = (time.monotonic(), result)
            if len(self._entries) > MAX_ENTRIES:
                oldest = next(iter(self._entries))
                del self._entries[oldest]
                self._locks.pop(oldest, None)
            return result
