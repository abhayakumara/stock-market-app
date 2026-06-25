"""AI endpoints (Claude): market commentary and NL strategy authoring.

Both return 503 when the Anthropic key/SDK is unavailable, so the app degrades cleanly.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.ai import AIClient, AIUnavailable
from app.config import Settings, get_settings
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
