"""The live-trading controller — the single chokepoint every real order passes through.

It owns the kill switch (``armed``), the risk-disclosure acknowledgement, the set of
promoted strategies, the configurable risk limits, and the running daily realized loss.
``authorize()`` enforces all five gates in order and raises :class:`LiveRejected` with a
clear reason on the first failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.models import Order

from .risk import RiskLimits, RiskManager


class LiveRejected(Exception):
    """A real order was blocked by one of the live-trading gates."""


@dataclass
class LiveController:
    configured: bool = False  # Kite keys + daily access token present
    acknowledged: bool = False  # user accepted the real-money risk disclosure
    armed: bool = False  # global kill switch (OFF by default)
    limits: RiskLimits = field(default_factory=RiskLimits)
    promoted: set[str] = field(default_factory=set)
    daily_loss: Decimal = Decimal("0")  # positive = realized losses today

    def __post_init__(self) -> None:
        self._risk = RiskManager(self.limits)

    # ---- operator controls -------------------------------------------------
    def acknowledge(self) -> None:
        self.acknowledged = True

    def arm(self) -> None:
        """Turn the kill switch ON. Requires configuration + acknowledgement first."""
        if not self.configured:
            raise LiveRejected("cannot arm: live trading is not configured (Kite login required)")
        if not self.acknowledged:
            raise LiveRejected("cannot arm: the real-money risk disclosure must be acknowledged")
        self.armed = True

    def disarm(self) -> None:
        """Turn the kill switch OFF. Always allowed — this is the emergency stop."""
        self.armed = False

    def set_limits(self, limits: RiskLimits) -> None:
        self.limits = limits
        self._risk = RiskManager(limits)

    def promote(self, strategy_id: str) -> None:
        self.promoted.add(strategy_id)

    def demote(self, strategy_id: str) -> None:
        self.promoted.discard(strategy_id)

    def record_realized(self, pnl: Decimal) -> None:
        """Feed a realized P&L delta; losses accumulate toward the daily-loss cap."""
        if pnl < 0:
            self.daily_loss += -pnl

    def reset_day(self) -> None:
        self.daily_loss = Decimal("0")

    # ---- the gate ----------------------------------------------------------
    def authorize(
        self,
        order: Order,
        *,
        reference_price: Decimal,
        current_net_qty: int = 0,
        current_position_value: Decimal = Decimal("0"),
        open_positions: int = 0,
        strategy_id: str | None = None,
    ) -> None:
        """Raise :class:`LiveRejected` unless the order clears every gate."""
        if not self.configured:
            raise LiveRejected("live trading is not configured (Kite keys + daily login required)")
        if not self.acknowledged:
            raise LiveRejected("real-money risk disclosure has not been acknowledged")
        if not self.armed:
            raise LiveRejected("live trading is disarmed (kill switch is OFF)")
        if strategy_id is not None and strategy_id not in self.promoted:
            raise LiveRejected(
                f"strategy '{strategy_id}' is not promoted for real-money trading"
            )
        decision = self._risk.check(
            order,
            reference_price=reference_price,
            current_net_qty=current_net_qty,
            current_position_value=current_position_value,
            open_positions=open_positions,
            daily_loss=self.daily_loss,
        )
        if not decision.ok:
            raise LiveRejected(decision.reason)

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "acknowledged": self.acknowledged,
            "armed": self.armed,
            "promoted": sorted(self.promoted),
            "daily_loss": str(self.daily_loss),
            "limits": self.limits.as_dict(),
        }
