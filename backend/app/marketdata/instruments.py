"""A small seed of NSE instruments used for the mock feed and demo watchlist.

In production this is replaced by the daily Kite instruments dump (``kite.instruments()``)
loaded into Postgres. Tokens here are illustrative.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_token: int
    tradingsymbol: str
    name: str
    exchange: str
    seed_price: Decimal


SEED_INSTRUMENTS: list[Instrument] = [
    Instrument(256265, "NIFTY 50", "NIFTY 50 Index", "NSE", Decimal("23500")),
    Instrument(260105, "BANKNIFTY", "Nifty Bank Index", "NSE", Decimal("51000")),
    Instrument(738561, "RELIANCE", "Reliance Industries", "NSE", Decimal("2900")),
    Instrument(341249, "HDFCBANK", "HDFC Bank", "NSE", Decimal("1650")),
    Instrument(408065, "INFY", "Infosys", "NSE", Decimal("1850")),
    Instrument(2953217, "TCS", "Tata Consultancy Services", "NSE", Decimal("4100")),
    Instrument(1270529, "ICICIBANK", "ICICI Bank", "NSE", Decimal("1180")),
    Instrument(225537, "TATAMOTORS", "Tata Motors", "NSE", Decimal("980")),
]

BY_TOKEN = {i.instrument_token: i for i in SEED_INSTRUMENTS}
BY_SYMBOL = {i.tradingsymbol: i for i in SEED_INSTRUMENTS}
