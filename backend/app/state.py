"""Process-wide application state for the MVP.

A single paper account and one market hub per process. The hub feeds every tick into the
broker so resting paper orders fill in real time. Multi-user accounts and DB persistence
arrive in a later phase; the interfaces here are deliberately small so that swap is
localized.
"""

from __future__ import annotations

from decimal import Decimal

from app.config import Settings
from app.marketdata.hub import MarketHub
from app.marketdata.instruments import SEED_INSTRUMENTS
from app.marketdata.source import KiteTickSource, MockReplaySource, TickSource
from app.paper.engine import PaperBroker


class AppState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.broker = PaperBroker(initial_capital=Decimal("1000000"))
        self.hub = MarketHub(self._build_source(settings))
        # Wire the feed into the broker so paper orders match against live ticks.
        self.hub.on_tick = self.broker.on_tick

    def _build_source(self, settings: Settings) -> TickSource:
        if settings.use_mock_market_data or not settings.kite_configured:
            return MockReplaySource()
        # Real feed requires a live access token (obtained via the daily login flow);
        # until then the mock source keeps the app usable.
        tokens = [i.instrument_token for i in SEED_INSTRUMENTS]
        return KiteTickSource(settings.kite_api_key, access_token="", tokens=tokens)

    async def start(self) -> None:
        await self.hub.start()

    async def stop(self) -> None:
        await self.hub.stop()
