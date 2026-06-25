"""Brokerage and statutory charges model for NSE equity.

These rates approximate Zerodha's published charge structure for NSE equity so that
paper-trading P&L reflects real-world costs. They are configurable and clearly
*approximate* — they are not a substitute for the contract note. Rates are expressed as
fractions (e.g. 0.0003 == 0.03%).

Defaults (NSE equity, as commonly published):
  - Brokerage: delivery (CNC) = 0; intraday (MIS) = min(0.03%, ₹20) per executed order.
  - STT: delivery = 0.1% on buy & sell; intraday = 0.025% on the SELL side only.
  - Exchange txn charge: ~0.00297% of turnover.
  - SEBI charges: ₹10 per crore  = 0.0001% of turnover.
  - GST: 18% on (brokerage + SEBI + txn charges).
  - Stamp duty: delivery = 0.015% on BUY; intraday = 0.003% on BUY (buy side only).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import Segment, Side

_PAISE = Decimal("0.01")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(_PAISE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class ChargesModel:
    # Brokerage
    intraday_brokerage_rate: Decimal = Decimal("0.0003")  # 0.03%
    intraday_brokerage_cap: Decimal = Decimal("20")  # ₹20 per order
    delivery_brokerage_rate: Decimal = Decimal("0")

    # STT
    stt_delivery_rate: Decimal = Decimal("0.001")  # 0.1% both sides
    stt_intraday_sell_rate: Decimal = Decimal("0.00025")  # 0.025% sell only

    # Exchange + regulator
    exchange_txn_rate: Decimal = Decimal("0.0000297")  # 0.00297%
    sebi_rate: Decimal = Decimal("0.000001")  # ₹10/crore
    gst_rate: Decimal = Decimal("0.18")

    # Stamp duty (buy side only)
    stamp_delivery_rate: Decimal = Decimal("0.00015")  # 0.015%
    stamp_intraday_rate: Decimal = Decimal("0.00003")  # 0.003%

    def brokerage(self, turnover: Decimal, segment: Segment) -> Decimal:
        if segment is Segment.EQUITY_DELIVERY:
            return _round2(turnover * self.delivery_brokerage_rate)
        raw = turnover * self.intraday_brokerage_rate
        return _round2(min(raw, self.intraday_brokerage_cap))

    def stt(self, turnover: Decimal, segment: Segment, side: Side) -> Decimal:
        if segment is Segment.EQUITY_DELIVERY:
            return _round2(turnover * self.stt_delivery_rate)
        # intraday: sell side only
        if side is Side.SELL:
            return _round2(turnover * self.stt_intraday_sell_rate)
        return Decimal("0")

    def stamp_duty(self, turnover: Decimal, segment: Segment, side: Side) -> Decimal:
        if side is not Side.BUY:
            return Decimal("0")
        rate = (
            self.stamp_delivery_rate
            if segment is Segment.EQUITY_DELIVERY
            else self.stamp_intraday_rate
        )
        return _round2(turnover * rate)

    def compute(
        self,
        *,
        price: Decimal,
        quantity: int,
        side: Side,
        segment: Segment,
    ) -> Decimal:
        """Total charges for a single executed leg (one buy or one sell)."""
        turnover = price * quantity
        brokerage = self.brokerage(turnover, segment)
        exchange_txn = _round2(turnover * self.exchange_txn_rate)
        sebi = _round2(turnover * self.sebi_rate)
        gst = _round2((brokerage + exchange_txn + sebi) * self.gst_rate)
        stt = self.stt(turnover, segment, side)
        stamp = self.stamp_duty(turnover, segment, side)
        return brokerage + exchange_txn + sebi + gst + stt + stamp
