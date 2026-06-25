"""In-process market-data hub.

Runs a :class:`TickSource` in a background task, keeps the latest price per instrument,
feeds every tick to the paper broker (so resting orders fill), and fans ticks out to any
number of async subscribers (e.g. WebSocket clients).

For a single-process MVP this in-memory hub is sufficient. The production design swaps
the fan-out for Redis pub/sub so multiple API workers share one Kite WebSocket
connection (which is limited to one per API key).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from decimal import Decimal

from app.domain.models import Tick

from .source import TickSource


class MarketHub:
    def __init__(self, source: TickSource):
        self._source = source
        self._subscribers: set[asyncio.Queue[Tick]] = set()
        self._latest: dict[int, Tick] = {}
        self._task: asyncio.Task | None = None
        # Optional consumer (the paper broker's on_tick) invoked for every tick.
        self.on_tick = None

    @property
    def latest_prices(self) -> dict[int, Decimal]:
        return {token: t.last_price for token, t in self._latest.items()}

    def latest(self, instrument_token: int) -> Tick | None:
        return self._latest.get(instrument_token)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        async for tick in self._source.stream():
            self._latest[tick.instrument_token] = tick
            if self.on_tick is not None:
                try:
                    self.on_tick(tick)
                except Exception:  # a broker error must not kill the feed
                    pass
            for q in list(self._subscribers):
                # Drop ticks for slow consumers rather than blocking the feed.
                if q.full():
                    with contextlib.suppress(asyncio.QueueEmpty):
                        q.get_nowait()
                q.put_nowait(tick)

    async def subscribe(self) -> AsyncIterator[Tick]:
        q: asyncio.Queue[Tick] = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subscribers.discard(q)
