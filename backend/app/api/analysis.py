"""Analysis endpoints: candles, indicator series, and screeners."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analysis import indicators as ind
from app.analysis.candles import closes
from app.analysis.screener import SCANS, run_scan
from app.marketdata.instruments import SEED_INSTRUMENTS
from app.state import AppState

from .deps import get_state

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/candles/{instrument_token}")
def candles(
    instrument_token: int,
    count: int = Query(300, ge=10, le=1000),
    interval_minutes: int = Query(5, ge=1, le=60),
    state: AppState = Depends(get_state),
) -> dict:
    cs = state.get_candles(instrument_token, count=count, interval_minutes=interval_minutes)
    return {
        "instrument_token": instrument_token,
        "interval_minutes": interval_minutes,
        "candles": [c.as_dict() for c in cs],
    }


@router.get("/indicators/{instrument_token}")
def indicators(
    instrument_token: int,
    count: int = Query(300, ge=10, le=1000),
    interval_minutes: int = Query(5, ge=1, le=60),
    state: AppState = Depends(get_state),
) -> dict:
    cs = state.get_candles(instrument_token, count=count, interval_minutes=interval_minutes)
    src = closes(cs)
    macd_line, macd_signal, macd_hist = ind.macd(src)
    boll_mid, boll_upper, boll_lower = ind.bollinger(src, 20)
    return {
        "instrument_token": instrument_token,
        "timestamps": [c.timestamp.isoformat() for c in cs],
        "close": src,
        "sma20": ind.sma(src, 20),
        "sma50": ind.sma(src, 50),
        "ema20": ind.ema(src, 20),
        "rsi14": ind.rsi(src, 14),
        "macd": macd_line,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "boll_upper": boll_upper,
        "boll_mid": boll_mid,
        "boll_lower": boll_lower,
    }


@router.get("/screener")
def screener(
    scan: str = Query(..., description=f"One of: {', '.join(SCANS)}"),
    count: int = Query(300, ge=50, le=1000),
    interval_minutes: int = Query(5, ge=1, le=60),
    state: AppState = Depends(get_state),
) -> dict:
    if scan not in SCANS:
        raise HTTPException(status_code=400, detail=f"unknown scan; choose from {list(SCANS)}")
    hits = run_scan(
        scan,
        SEED_INSTRUMENTS,
        lambda token: state.get_candles(token, count=count, interval_minutes=interval_minutes),
    )
    return {
        "scan": scan,
        "available_scans": list(SCANS),
        "hits": [
            {
                "instrument_token": h.instrument_token,
                "tradingsymbol": h.tradingsymbol,
                "detail": h.detail,
            }
            for h in hits
        ],
    }


@router.get("/scans")
def scans() -> dict:
    return {"scans": list(SCANS)}
