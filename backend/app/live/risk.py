"""Pre-trade risk controls for real-money orders.

Conservative defaults that the user can adjust. The manager is a pure function of the
order plus the current account snapshot, so it is fully unit-testable and identical in
behavior every time.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.models import Order


@dataclass(slots=True)
class RiskLimits:
    max_order_value: Decimal = Decimal("10000")  # ₹ notional per single order
    max_position_value: Decimal = Decimal("25000")  # ₹ notional per instrument
    max_daily_loss: Decimal = Decimal("5000")  # ₹ realized loss before trading halts
    max_open_positions: int = 5

    def as_dict(self) -> dict:
        return {
            "max_order_value": str(self.max_order_value),
            "max_position_value": str(self.max_position_value),
            "max_daily_loss": str(self.max_daily_loss),
            "max_open_positions": self.max_open_positions,
        }


@dataclass(frozen=True, slots=True)
class RiskDecision:
    ok: bool
    reason: str = ""


class RiskManager:
    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()

    def check(
        self,
        order: Order,
        *,
        reference_price: Decimal,
        current_net_qty: int,
        current_position_value: Decimal,
        open_positions: int,
        daily_loss: Decimal,
    ) -> RiskDecision:
        """``daily_loss`` is a positive number representing realized losses so far today."""
        lim = self.limits

        if daily_loss >= lim.max_daily_loss:
            return RiskDecision(
                False,
                f"daily loss ₹{daily_loss} has reached the cap ₹{lim.max_daily_loss}; "
                "trading is halted for the day",
            )

        order_value = reference_price * order.quantity
        if order_value > lim.max_order_value:
            return RiskDecision(
                False,
                f"order value ₹{order_value:.0f} exceeds the per-order cap "
                f"₹{lim.max_order_value}",
            )

        signed = order.side.sign * order.quantity
        increasing = current_net_qty == 0 or (current_net_qty > 0) == (signed > 0)

        if increasing:
            projected = current_position_value + order_value
            if projected > lim.max_position_value:
                return RiskDecision(
                    False,
                    f"position value would reach ₹{projected:.0f}, above the per-instrument "
                    f"cap ₹{lim.max_position_value}",
                )
            if current_net_qty == 0 and open_positions >= lim.max_open_positions:
                return RiskDecision(
                    False,
                    f"already at the max of {lim.max_open_positions} open positions",
                )

        return RiskDecision(True)
