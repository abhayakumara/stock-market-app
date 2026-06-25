"""Enumerations shared across the trading domain.

Names mirror Zerodha Kite Connect conventions so the same order objects can flow
through both the in-house paper engine and the real live-order service unchanged.
"""

from __future__ import annotations

from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> int:
        """+1 for BUY, -1 for SELL — used for signed position math."""
        return 1 if self is Side.BUY else -1


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # stop-loss limit (trigger + limit price)
    SL_M = "SL-M"  # stop-loss market (trigger only)


class Product(str, Enum):
    CNC = "CNC"  # equity delivery
    MIS = "MIS"  # intraday (margin)
    NRML = "NRML"  # F&O / overnight


class OrderStatus(str, Enum):
    PENDING = "PENDING"  # accepted, not yet resting in book
    OPEN = "OPEN"  # resting, awaiting trigger/price
    COMPLETE = "COMPLETE"  # fully filled
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Segment(str, Enum):
    """Charge segment — determines brokerage/STT/stamp-duty schedule."""

    EQUITY_DELIVERY = "EQUITY_DELIVERY"
    EQUITY_INTRADAY = "EQUITY_INTRADAY"


class TradingMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"
