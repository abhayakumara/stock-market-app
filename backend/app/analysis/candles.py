"""Candle (OHLCV) types, live aggregation from ticks, and historical providers.

* :class:`CandleAggregator` rolls a live tick stream into fixed-interval candles so the
  Analysis view always has an up-to-date chart even in mock mode.
* :class:`SyntheticCandleProvider` produces deterministic historical candles (seeded
  random walk) so the chart, screener, and backtester all work with **no Zerodha
  account**.
* :class:`KiteCandleProvider` fetches real historical candles via ``kite.historical_data``
  when credentials + a live access token are available (lazy import keeps it optional).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.models import Tick


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


def closes(candles: list[Candle]) -> list[float]:
    return [c.close for c in candles]


class CandleAggregator:
    """Rolls ticks into fixed-interval candles, keeping a bounded recent history."""

    def __init__(self, interval_seconds: int = 60, max_candles: int = 500):
        self.interval = interval_seconds
        self.max_candles = max_candles
        self._candles: dict[int, list[Candle]] = {}
        self._open: dict[int, Candle] = {}

    def _bucket(self, ts: datetime) -> datetime:
        epoch = int(ts.timestamp())
        floored = epoch - (epoch % self.interval)
        return datetime.fromtimestamp(floored, tz=UTC)

    def add(self, tick: Tick) -> None:
        token = tick.instrument_token
        price = float(tick.last_price)
        vol = float(tick.volume or 0)
        bucket = self._bucket(tick.timestamp)
        current = self._open.get(token)
        if current is None or current.timestamp != bucket:
            if current is not None:
                self._commit(token, current)
            self._open[token] = Candle(bucket, price, price, price, price, vol)
            return
        self._open[token] = Candle(
            timestamp=current.timestamp,
            open=current.open,
            high=max(current.high, price),
            low=min(current.low, price),
            close=price,
            volume=current.volume + vol,
        )

    def _commit(self, token: int, candle: Candle) -> None:
        series = self._candles.setdefault(token, [])
        series.append(candle)
        if len(series) > self.max_candles:
            del series[: len(series) - self.max_candles]

    def candles(self, token: int) -> list[Candle]:
        """Committed candles plus the in-progress one."""
        series = list(self._candles.get(token, []))
        if token in self._open:
            series.append(self._open[token])
        return series


class SyntheticCandleProvider:
    """Deterministic historical candles via a seeded random walk (offline-friendly)."""

    def __init__(self, volatility: float = 0.012):
        self.volatility = volatility

    def history(
        self,
        instrument_token: int,
        seed_price: Decimal,
        count: int = 300,
        interval_minutes: int = 5,
    ) -> list[Candle]:
        rng = random.Random(instrument_token)  # deterministic per instrument
        price = float(seed_price)
        now = datetime.now(UTC)
        candles: list[Candle] = []
        for i in range(count):
            ts = now - timedelta(minutes=interval_minutes * (count - i))
            drift = rng.uniform(-1, 1) * self.volatility
            open_ = price
            close = max(0.05, open_ * (1 + drift))
            high = max(open_, close) * (1 + abs(rng.uniform(0, self.volatility)))
            low = min(open_, close) * (1 - abs(rng.uniform(0, self.volatility)))
            volume = rng.randint(1000, 100000)
            candles.append(Candle(ts, round(open_, 2), round(high, 2), round(low, 2),
                                  round(close, 2), volume))
            price = close
        return candles


class KiteCandleProvider:
    """Real historical candles via the Kite REST API (requires a live access token)."""

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token

    def history(
        self, instrument_token: int, count: int = 300, interval: str = "5minute"
    ) -> list[Candle]:
        from kiteconnect import KiteConnect  # lazy optional import

        kite = KiteConnect(api_key=self.api_key)
        kite.set_access_token(self.access_token)
        to_dt = datetime.now(UTC)
        from_dt = to_dt - timedelta(days=30)
        rows = kite.historical_data(instrument_token, from_dt, to_dt, interval)
        candles = [
            Candle(
                timestamp=r["date"],
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r.get("volume", 0)),
            )
            for r in rows
        ]
        return candles[-count:]
