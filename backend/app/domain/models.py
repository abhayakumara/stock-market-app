"""Core domain dataclasses: ticks, orders, trades, positions.

Pure Python + ``Decimal`` so the paper engine and its tests run with no external
dependencies (no DB, no network). Money and prices use ``Decimal`` to avoid binary
float drift in P&L and charge calculations.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from .enums import OrderStatus, OrderType, Product, Side


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Tick:
    """A single market data update for one instrument."""

    instrument_token: int
    last_price: Decimal
    timestamp: datetime = field(default_factory=_now)
    # Optional top-of-book; when present the fill engine prefers them over last_price.
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: int | None = None


_order_ids = itertools.count(1)


@dataclass(slots=True)
class Order:
    """An order request/working order. Mutable: status and fills evolve over time."""

    instrument_token: int
    side: Side
    quantity: int
    order_type: OrderType
    product: Product
    tradingsymbol: str = ""
    limit_price: Decimal | None = None
    trigger_price: Decimal | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: Decimal | None = None
    order_id: str = ""
    created_at: datetime = field(default_factory=_now)
    # Set true once an SL/SL-M order's trigger has fired and it became active.
    triggered: bool = False
    reject_reason: str = ""

    def __post_init__(self) -> None:
        if not self.order_id:
            self.order_id = f"PAPER-{next(_order_ids):08d}"
        self._validate()

    def _validate(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type in (OrderType.LIMIT, OrderType.SL) and self.limit_price is None:
            raise ValueError(f"{self.order_type} order requires a limit_price")
        if self.order_type in (OrderType.SL, OrderType.SL_M) and self.trigger_price is None:
            raise ValueError(f"{self.order_type} order requires a trigger_price")

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.OPEN)


@dataclass(frozen=True, slots=True)
class Trade:
    """An executed fill produced by the paper engine."""

    order_id: str
    instrument_token: int
    side: Side
    quantity: int
    price: Decimal
    charges: Decimal
    timestamp: datetime = field(default_factory=_now)
    tradingsymbol: str = ""


@dataclass(slots=True)
class Position:
    """Net position in one instrument, with realized + unrealized P&L tracking.

    Uses average-cost accounting. ``net_quantity`` is signed (+long / -short).
    """

    instrument_token: int
    tradingsymbol: str = ""
    net_quantity: int = 0
    average_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_charges: Decimal = Decimal("0")
    last_price: Decimal = Decimal("0")

    def unrealized_pnl(self) -> Decimal:
        if self.net_quantity == 0:
            return Decimal("0")
        return (self.last_price - self.average_price) * self.net_quantity
