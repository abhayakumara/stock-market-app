"""Market screeners/scanners.

Each scan inspects a symbol's recent candles and returns whether it currently matches,
plus a few supporting numbers for display. Scans run over the seed instrument set using
whatever candle provider the caller passes (synthetic offline, Kite when live).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.analysis import indicators as ind
from app.analysis.candles import Candle, closes


@dataclass(frozen=True, slots=True)
class ScanHit:
    scan: str
    instrument_token: int
    tradingsymbol: str
    detail: dict


def _rsi_oversold(candles: list[Candle]) -> dict | None:
    rsi = ind.rsi(closes(candles), 14)
    v = rsi[-1] if rsi else None
    if v is not None and v < 30:
        return {"rsi": round(v, 2)}
    return None


def _rsi_overbought(candles: list[Candle]) -> dict | None:
    rsi = ind.rsi(closes(candles), 14)
    v = rsi[-1] if rsi else None
    if v is not None and v > 70:
        return {"rsi": round(v, 2)}
    return None


def _golden_cross(candles: list[Candle]) -> dict | None:
    src = closes(candles)
    fast = ind.sma(src, 20)
    slow = ind.sma(src, 50)
    if len(src) < 51:
        return None
    if fast[-1] is None or slow[-1] is None or fast[-2] is None or slow[-2] is None:
        return None
    crossed_up = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
    if crossed_up:
        return {"sma20": round(fast[-1], 2), "sma50": round(slow[-1], 2)}
    return None


def _above_200sma(candles: list[Candle]) -> dict | None:
    src = closes(candles)
    sma200 = ind.sma(src, 200)
    if not sma200 or sma200[-1] is None:
        return None
    if src[-1] > sma200[-1]:
        return {"close": round(src[-1], 2), "sma200": round(sma200[-1], 2)}
    return None


def _breakout_20(candles: list[Candle]) -> dict | None:
    """Close breaks above the prior 20-bar high."""
    if len(candles) < 21:
        return None
    prior_high = max(c.high for c in candles[-21:-1])
    last = candles[-1].close
    if last > prior_high:
        return {"close": round(last, 2), "prior_high": round(prior_high, 2)}
    return None


SCANS: dict[str, Callable[[list[Candle]], dict | None]] = {
    "rsi_oversold": _rsi_oversold,
    "rsi_overbought": _rsi_overbought,
    "golden_cross": _golden_cross,
    "above_200sma": _above_200sma,
    "breakout_20": _breakout_20,
}


def run_scan(
    scan: str,
    universe: list,  # list[Instrument]
    get_candles: Callable[[int], list[Candle]],
) -> list[ScanHit]:
    if scan not in SCANS:
        raise ValueError(f"unknown scan: {scan}")
    fn = SCANS[scan]
    hits: list[ScanHit] = []
    for inst in universe:
        candles = get_candles(inst.instrument_token)
        detail = fn(candles)
        if detail is not None:
            hits.append(
                ScanHit(
                    scan=scan,
                    instrument_token=inst.instrument_token,
                    tradingsymbol=inst.tradingsymbol,
                    detail=detail,
                )
            )
    return hits
