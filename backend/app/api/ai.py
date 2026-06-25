"""AI endpoints (Claude): market commentary and NL strategy authoring.

Both return 503 when the Anthropic key/SDK is unavailable, so the app degrades cleanly.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.ai import AIClient, AIUnavailable
from app.config import Settings, get_settings
from app.journal import summarize_trades
from app.marketdata.instruments import BY_TOKEN
from app.state import AppState

from .deps import get_state

router = APIRouter(prefix="/ai", tags=["ai"])


class AuthorStrategyIn(BaseModel):
    prompt: str


def _client(settings: Settings) -> AIClient:
    try:
        return AIClient(settings.anthropic_api_key)
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/commentary/{instrument_token}")
def commentary(
    instrument_token: int,
    state: AppState = Depends(get_state),
    settings: Settings = Depends(get_settings),
) -> dict:
    client = _client(settings)
    inst = BY_TOKEN.get(instrument_token)
    symbol = inst.tradingsymbol if inst else "instrument"
    candles = state.get_candles(instrument_token, count=120)
    try:
        text = client.commentary(symbol, candles)
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"instrument_token": instrument_token, "symbol": symbol, "commentary": text}


@router.post("/strategy")
def author_strategy(
    payload: AuthorStrategyIn, settings: Settings = Depends(get_settings)
) -> dict:
    client = _client(settings)
    try:
        config = client.author_strategy(payload.prompt)
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"AI produced an invalid strategy: {exc}"
        ) from exc
    return {"config": config}


@router.get("/coach")
def coach(
    state: AppState = Depends(get_state), settings: Settings = Depends(get_settings)
) -> dict:
    client = _client(settings)
    s = state.broker.summary()
    account = {
        "equity": str(s.equity),
        "cash": str(s.cash),
        "realized_pnl": str(s.realized_pnl),
        "unrealized_pnl": str(s.unrealized_pnl),
        "total_charges": str(s.total_charges),
    }
    positions = [
        {
            "symbol": p.tradingsymbol,
            "qty": p.net_quantity,
            "avg": str(p.average_price),
            "unrealized": str(p.unrealized_pnl()),
        }
        for p in state.broker.positions.values()
    ]
    summary = summarize_trades(state.broker.trades)
    try:
        text = client.coach(account, positions, summary)
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"coaching": text}


@router.get("/review")
def review(
    state: AppState = Depends(get_state), settings: Settings = Depends(get_settings)
) -> dict:
    client = _client(settings)
    summary = summarize_trades(state.broker.trades)
    if summary["closed_trades"] == 0:
        return {"review": "No closed trades yet — make a few paper trades to get a review."}
    try:
        text = client.review_trades(summary)
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"review": text}
