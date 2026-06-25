"""Process-wide application state.

This is a **single-user** application (decided during planning): one paper account, one
market hub, and one candle aggregator per process. No per-user scoping or auth — the
local operator is the only user. DB persistence can be layered in later behind these same
small interfaces.
"""

from __future__ import annotations

from decimal import Decimal

from app.analysis.candles import (
    Candle,
    CandleAggregator,
    KiteCandleProvider,
    SyntheticCandleProvider,
)
from app.config import Settings
from app.domain.models import Tick
from app.marketdata.hub import MarketHub
from app.marketdata.instruments import BY_TOKEN, SEED_INSTRUMENTS
from app.marketdata.source import KiteTickSource, MockReplaySource, TickSource
from app.paper.engine import PaperBroker


class AppState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.broker = PaperBroker(initial_capital=Decimal("1000000"))
        self.aggregator = CandleAggregator(interval_seconds=60)
        self.synthetic = SyntheticCandleProvider()
        # Saved strategies authored in the UI / by the AI (single-user, in-memory).
        self.strategies: list[dict] = []
        self._kite_access_token: str = ""

        self.hub = MarketHub(self._build_source(settings))
        # Every tick feeds both the broker (fills resting orders) and the aggregator
        # (builds live candles for the chart).
        self.hub.on_tick = self._on_tick

    def _on_tick(self, tick: Tick) -> None:
        self.broker.on_tick(tick)
        self.aggregator.add(tick)

    def _build_source(self, settings: Settings) -> TickSource:
        if settings.use_mock_market_data or not settings.kite_configured:
            return MockReplaySource()
        tokens = [i.instrument_token for i in SEED_INSTRUMENTS]
        return KiteTickSource(settings.kite_api_key, access_token="", tokens=tokens)

    def set_kite_access_token(self, token: str) -> None:
        """Store the daily Kite access token (in memory) for historical-data calls."""
        self._kite_access_token = token

    def get_candles(
        self, instrument_token: int, count: int = 300, interval_minutes: int = 5
    ) -> list[Candle]:
        """Historical candles for charts/indicators/backtests.

        Uses real Kite history when a live access token is available; otherwise a
        deterministic synthetic series so the whole app works with no Zerodha account.
        """
        if self.settings.kite_configured and self._kite_access_token:
            try:
                provider = KiteCandleProvider(self.settings.kite_api_key, self._kite_access_token)
                return provider.history(
                    instrument_token, count=count, interval=f"{interval_minutes}minute"
                )
            except Exception:
                pass  # fall back to synthetic on any data error
        seed = (
            BY_TOKEN[instrument_token].seed_price
            if instrument_token in BY_TOKEN
            else Decimal("1000")
        )
        return self.synthetic.history(
            instrument_token, seed, count=count, interval_minutes=interval_minutes
        )

    async def start(self) -> None:
        await self.hub.start()

    async def stop(self) -> None:
        await self.hub.stop()
