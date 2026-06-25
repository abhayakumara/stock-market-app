"""Tick-driven paper-trading broker.

The :class:`PaperBroker` accepts orders and matches them against incoming :class:`Tick`
updates, applying configurable slippage and the :class:`ChargesModel`. It maintains a
virtual cash ledger and average-cost positions with realized/unrealized P&L.

Design notes:
* **Tick-driven.** Orders rest until a tick makes them marketable; this mirrors how the
  live feed actually drives execution and keeps paper/live behavior aligned.
* **Conservative limit fills.** A LIMIT order fills at its limit price (or better if the
  tick is strictly better), never worse — the realistic worst case for the trader.
* **Decimal money.** All prices/cash use ``Decimal`` to avoid float drift in P&L.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import OrderStatus, OrderType, Product, Segment, Side
from app.domain.models import Order, Position, Tick

from .charges import ChargesModel

_PAISE = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_PAISE, rounding=ROUND_HALF_UP)


def _segment_for(product: Product) -> Segment:
    return Segment.EQUITY_INTRADAY if product is Product.MIS else Segment.EQUITY_DELIVERY


@dataclass(slots=True)
class AccountSummary:
    cash: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_charges: Decimal

    @property
    def equity(self) -> Decimal:
        # cash already reflects all completed cash flows; add open-position mark-to-market.
        return self.cash + self.unrealized_pnl


class InsufficientFundsError(Exception):
    """Raised when an order would exceed available buying power."""


@dataclass
class PaperBroker:
    """A single virtual trading account with a tick-driven matching engine."""

    initial_capital: Decimal = Decimal("1000000")
    charges: ChargesModel = field(default_factory=ChargesModel)
    slippage: Decimal = Decimal("0.0005")  # 5 bps applied to market/SL-M fills
    mis_leverage: Decimal = Decimal("5")  # intraday buying-power multiplier

    cash: Decimal = field(init=False)
    positions: dict[int, Position] = field(init=False, default_factory=dict)
    orders: dict[str, Order] = field(init=False, default_factory=dict)
    trades: list = field(init=False, default_factory=list)
    _last_price: dict[int, Decimal] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.cash = Decimal(self.initial_capital)

    # ------------------------------------------------------------------ orders
    def place_order(self, order: Order) -> Order:
        """Register an order. Market orders fill immediately if a price is known,
        otherwise on the next tick. Raises :class:`InsufficientFundsError` if the order
        would exceed buying power."""
        self._check_buying_power(order)
        order.status = OrderStatus.OPEN
        self.orders[order.order_id] = order

        last = self._last_price.get(order.instrument_token)
        if last is not None:
            self._try_fill(order, Tick(order.instrument_token, last))
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self.orders[order_id]
        if order.is_active:
            order.status = OrderStatus.CANCELLED
        return order

    def get_position(self, instrument_token: int) -> Position | None:
        return self.positions.get(instrument_token)

    def summary(self) -> AccountSummary:
        realized = sum((p.realized_pnl for p in self.positions.values()), Decimal("0"))
        unrealized = sum((p.unrealized_pnl() for p in self.positions.values()), Decimal("0"))
        charges = sum((p.total_charges for p in self.positions.values()), Decimal("0"))
        return AccountSummary(
            cash=_q(self.cash),
            realized_pnl=_q(realized),
            unrealized_pnl=_q(unrealized),
            total_charges=_q(charges),
        )

    # -------------------------------------------------------------------- ticks
    def on_tick(self, tick: Tick) -> list:
        """Feed a market tick; returns the list of trades executed by this tick."""
        self._last_price[tick.instrument_token] = tick.last_price
        pos = self.positions.get(tick.instrument_token)
        if pos is not None:
            pos.last_price = tick.last_price

        executed: list = []
        for order in list(self.orders.values()):
            if not order.is_active or order.instrument_token != tick.instrument_token:
                continue
            trade = self._try_fill(order, tick)
            if trade is not None:
                executed.append(trade)
        return executed

    # ----------------------------------------------------------------- internals
    def _check_buying_power(self, order: Order) -> None:
        ref = self._reference_price(order) or Decimal("0")
        if ref <= 0:
            return  # cannot price yet; checked again at fill time
        # Only exposure-increasing quantity consumes margin.
        pos = self.positions.get(order.instrument_token)
        net = pos.net_quantity if pos else 0
        signed = order.side.sign * order.quantity
        if net == 0 or (net > 0) == (signed > 0):
            increasing_qty = order.quantity
        else:
            increasing_qty = max(0, order.quantity - abs(net))
        if increasing_qty == 0:
            return
        leverage = self.mis_leverage if order.product is Product.MIS else Decimal("1")
        required = (ref * increasing_qty) / leverage
        if required > self.cash:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "insufficient funds"
            raise InsufficientFundsError(
                f"need {_q(required)} margin, have {_q(self.cash)}"
            )

    def _reference_price(self, order: Order) -> Decimal | None:
        if order.order_type in (OrderType.LIMIT, OrderType.SL):
            return order.limit_price
        if order.order_type is OrderType.SL_M:
            return order.trigger_price
        return self._last_price.get(order.instrument_token)

    def _try_fill(self, order: Order, tick: Tick) -> object | None:
        fill_price = self._match(order, tick)
        if fill_price is None:
            return None
        return self._execute(order, fill_price)

    def _match(self, order: Order, tick: Tick) -> Decimal | None:
        """Return the fill price if the order is marketable on this tick, else None."""
        px = tick.last_price

        # Activate stop orders once their trigger is breached.
        if order.order_type in (OrderType.SL, OrderType.SL_M) and not order.triggered:
            assert order.trigger_price is not None
            breached = (
                px >= order.trigger_price
                if order.side is Side.BUY
                else px <= order.trigger_price
            )
            if not breached:
                return None
            order.triggered = True

        if order.order_type is OrderType.MARKET or (
            order.order_type is OrderType.SL_M and order.triggered
        ):
            return self._market_price(order, tick)

        if order.order_type in (OrderType.LIMIT, OrderType.SL):
            assert order.limit_price is not None
            if order.side is Side.BUY and px <= order.limit_price:
                return min(order.limit_price, px)  # never worse than the limit
            if order.side is Side.SELL and px >= order.limit_price:
                return max(order.limit_price, px)
            return None
        return None

    def _market_price(self, order: Order, tick: Tick) -> Decimal:
        if order.side is Side.BUY:
            ref = tick.ask if tick.ask is not None else tick.last_price
            return _q(ref * (Decimal("1") + self.slippage))
        ref = tick.bid if tick.bid is not None else tick.last_price
        return _q(ref * (Decimal("1") - self.slippage))

    def _execute(self, order: Order, price: Decimal) -> object:
        from app.domain.models import Trade  # local import avoids cycle at module load

        qty = order.remaining_quantity
        segment = _segment_for(order.product)
        charges = self.charges.compute(
            price=price, quantity=qty, side=order.side, segment=segment
        )

        # Cash flow: BUY debits notional + charges; SELL credits notional - charges.
        notional = price * qty
        self.cash += Decimal(-order.side.sign) * notional - charges

        self._apply_to_position(order, qty, price, charges)

        order.filled_quantity += qty
        order.average_price = price
        order.status = OrderStatus.COMPLETE

        trade = Trade(
            order_id=order.order_id,
            instrument_token=order.instrument_token,
            side=order.side,
            quantity=qty,
            price=price,
            charges=charges,
            tradingsymbol=order.tradingsymbol,
        )
        self.trades.append(trade)
        return trade

    def _apply_to_position(
        self, order: Order, qty: int, price: Decimal, charges: Decimal
    ) -> None:
        pos = self.positions.get(order.instrument_token)
        if pos is None:
            pos = Position(
                instrument_token=order.instrument_token, tradingsymbol=order.tradingsymbol
            )
            self.positions[order.instrument_token] = pos

        pos.total_charges += charges
        pos.last_price = price
        signed = order.side.sign * qty
        q = pos.net_quantity

        if q == 0 or (q > 0) == (signed > 0):
            # Opening or increasing in the same direction → weighted average cost.
            new_abs = abs(q) + qty
            pos.average_price = (pos.average_price * abs(q) + price * qty) / new_abs
            pos.net_quantity = q + signed
            return

        # Reducing / closing / flipping.
        closing = min(qty, abs(q))
        direction = 1 if q > 0 else -1
        pos.realized_pnl += (price - pos.average_price) * closing * direction
        pos.net_quantity = q + signed
        remaining = qty - closing
        if pos.net_quantity == 0:
            pos.average_price = Decimal("0")
        elif remaining > 0:
            # Flipped to the opposite side; the leftover opens a fresh position.
            pos.average_price = price
