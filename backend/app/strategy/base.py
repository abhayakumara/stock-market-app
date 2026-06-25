"""Strategy interface and the target-signal type."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from app.analysis.candles import Candle


class Signal(str, Enum):
    """The position a strategy wants to hold going into the next bar."""

    LONG = "LONG"
    FLAT = "FLAT"
    SHORT = "SHORT"


class Strategy(Protocol):
    name: str

    def signal(self, candles: list[Candle], position: int) -> Signal:
        """Return the desired target position given history (incl. current bar) and the
        current signed position quantity."""
        ...
