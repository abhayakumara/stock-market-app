"""Instrument listing (seed set for the MVP / mock feed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.marketdata.instruments import SEED_INSTRUMENTS
from app.state import AppState

from .deps import get_state
from .schemas import InstrumentOut

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("", response_model=list[InstrumentOut])
def list_instruments(state: AppState = Depends(get_state)) -> list[InstrumentOut]:
    prices = state.hub.latest_prices
    return [
        InstrumentOut(
            instrument_token=i.instrument_token,
            tradingsymbol=i.tradingsymbol,
            name=i.name,
            exchange=i.exchange,
            last_price=prices.get(i.instrument_token, i.seed_price),
        )
        for i in SEED_INSTRUMENTS
    ]
