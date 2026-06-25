"""Simple price alerts, evaluated against the live tick stream.

A one-shot alert fires the first time its condition is met, then deactivates. Triggered
alerts are retained so the UI can show what fired (and when).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.models import Tick

_ids = itertools.count(1)


@dataclass(slots=True)
class Alert:
    instrument_token: int
    op: str  # ">" or "<"
    price: Decimal
    tradingsymbol: str = ""
    note: str = ""
    id: int = field(default_factory=lambda: next(_ids))
    active: bool = True
    triggered_at: datetime | None = None
    triggered_price: Decimal | None = None

    def matches(self, last_price: Decimal) -> bool:
        if self.op == ">":
            return last_price > self.price
        if self.op == "<":
            return last_price < self.price
        return False

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "instrument_token": self.instrument_token,
            "tradingsymbol": self.tradingsymbol,
            "op": self.op,
            "price": str(self.price),
            "note": self.note,
            "active": self.active,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "triggered_price": str(self.triggered_price) if self.triggered_price else None,
        }


class AlertBook:
    def __init__(self) -> None:
        self._alerts: dict[int, Alert] = {}

    def add(self, alert: Alert) -> Alert:
        self._alerts[alert.id] = alert
        return alert

    def remove(self, alert_id: int) -> bool:
        return self._alerts.pop(alert_id, None) is not None

    def list(self) -> list[Alert]:
        return list(self._alerts.values())

    def evaluate(self, tick: Tick) -> list[Alert]:
        """Return alerts newly triggered by this tick (and deactivate them)."""
        fired: list[Alert] = []
        for alert in self._alerts.values():
            if (
                alert.active
                and alert.instrument_token == tick.instrument_token
                and alert.matches(tick.last_price)
            ):
                alert.active = False
                alert.triggered_at = datetime.now(UTC)
                alert.triggered_price = tick.last_price
                fired.append(alert)
        return fired
