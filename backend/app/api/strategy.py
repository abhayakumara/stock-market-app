"""Strategy + backtest endpoints.

Templates are read-only presets. ``POST /backtest`` runs a strategy (template id or a
custom rule-DSL config) over historical candles using the shared paper-engine fill model.
Authored strategies can be saved in-process (single-user).
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.backtest import run_backtest
from app.domain.enums import Product
from app.state import AppState
from app.strategy import build_strategy
from app.strategy.library import TEMPLATES, list_templates

from .deps import get_state

router = APIRouter(prefix="/strategy", tags=["strategy"])


class BacktestIn(BaseModel):
    instrument_token: int
    template: str | None = Field(None, description="A built-in template id")
    config: dict | None = Field(None, description="A custom rule-DSL config")
    quantity: int = Field(10, gt=0)
    initial_capital: Decimal = Decimal("1000000")
    product: Product = Product.MIS
    candle_count: int = Field(300, ge=60, le=1000)
    interval_minutes: int = Field(5, ge=1, le=60)
    warmup: int = Field(50, ge=10, le=300)


class SaveStrategyIn(BaseModel):
    name: str
    config: dict


@router.get("/templates")
def templates() -> dict:
    return {"templates": list_templates()}


@router.post("/backtest")
def backtest(payload: BacktestIn, state: AppState = Depends(get_state)) -> dict:
    if payload.config is not None:
        config = payload.config
    elif payload.template is not None:
        if payload.template not in TEMPLATES:
            raise HTTPException(status_code=400, detail=f"unknown template: {payload.template}")
        config = TEMPLATES[payload.template]
    else:
        raise HTTPException(status_code=422, detail="provide either 'template' or 'config'")

    try:
        strategy = build_strategy(config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    candles = state.get_candles(
        payload.instrument_token,
        count=payload.candle_count,
        interval_minutes=payload.interval_minutes,
    )
    if payload.warmup >= len(candles):
        raise HTTPException(status_code=422, detail="warmup must be smaller than candle_count")

    result = run_backtest(
        candles=candles,
        strategy=strategy,
        instrument_token=payload.instrument_token,
        initial_capital=payload.initial_capital,
        quantity=payload.quantity,
        product=payload.product,
        warmup=payload.warmup,
    )
    return {"strategy": config.get("name", "custom"), **result.as_dict()}


@router.get("/saved")
def list_saved(state: AppState = Depends(get_state)) -> dict:
    return {"strategies": state.strategies}


@router.post("/saved")
def save(payload: SaveStrategyIn, state: AppState = Depends(get_state)) -> dict:
    try:
        build_strategy(payload.config)  # validate before saving
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    entry = {"name": payload.name, "config": payload.config}
    state.strategies.append(entry)
    return entry
