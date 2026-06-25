"""Tick sources.

``TickSource`` is an async iterator of :class:`Tick`. Two implementations:

* :class:`MockReplaySource` — a synthetic random-walk generator so the entire stack runs
  with no Zerodha account (gated by ``USE_MOCK_MARKET_DATA``).
* :class:`KiteTickSource` — wraps ``kiteconnect.KiteTicker`` (the real WebSocket feed).
  Imported lazily so the ``kiteconnect`` dependency stays optional.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Protocol

from app.domain.models import Tick

from .instruments import SEED_INSTRUMENTS


class TickSource(Protocol):
    def stream(self) -> AsyncIterator[Tick]: ...


class MockReplaySource:
    """Generates a random-walk price for each seed instrument at a fixed cadence."""

    def __init__(self, interval_seconds: float = 1.0, volatility: Decimal = Decimal("0.0008")):
        self.interval = interval_seconds
        self.volatility = volatility
        self._prices: dict[int, Decimal] = {
            i.instrument_token: i.seed_price for i in SEED_INSTRUMENTS
        }

    async def stream(self) -> AsyncIterator[Tick]:
        while True:
            for token, price in list(self._prices.items()):
                drift = Decimal(str(random.uniform(-1, 1))) * self.volatility
                new_price = (price * (Decimal("1") + drift)).quantize(Decimal("0.05"))
                if new_price <= 0:
                    new_price = price
                self._prices[token] = new_price
                spread = (new_price * Decimal("0.0002")).quantize(Decimal("0.05"))
                yield Tick(
                    instrument_token=token,
                    last_price=new_price,
                    bid=new_price - spread,
                    ask=new_price + spread,
                )
            await asyncio.sleep(self.interval)


class KiteTickSource:
    """Real Kite WebSocket feed. Requires the ``kiteconnect`` extra and a valid token.

    The Kite ``KiteTicker`` uses threaded callbacks; we bridge them onto an asyncio queue.
    """

    def __init__(self, api_key: str, access_token: str, tokens: list[int]):
        self.api_key = api_key
        self.access_token = access_token
        self.tokens = tokens
        self._queue: asyncio.Queue[Tick] = asyncio.Queue()

    async def stream(self) -> AsyncIterator[Tick]:
        from kiteconnect import KiteTicker  # lazy import; optional dependency

        loop = asyncio.get_running_loop()
        ticker = KiteTicker(self.api_key, self.access_token)

        def on_ticks(ws, ticks):  # runs on the ticker's thread
            for t in ticks:
                tick = Tick(
                    instrument_token=t["instrument_token"],
                    last_price=Decimal(str(t["last_price"])),
                    volume=t.get("volume_traded"),
                )
                loop.call_soon_threadsafe(self._queue.put_nowait, tick)

        def on_connect(ws, response):
            ws.subscribe(self.tokens)
            ws.set_mode(ws.MODE_FULL, self.tokens)

        ticker.on_ticks = on_ticks
        ticker.on_connect = on_connect
        ticker.connect(threaded=True)

        while True:
            yield await self._queue.get()
