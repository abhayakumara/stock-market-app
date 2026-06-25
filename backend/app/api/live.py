"""Real-money trading endpoints — the guarded path to live orders.

Every order placed here is authorized by the :class:`LiveController` (configured →
acknowledged → armed → promoted → risk-checked) before it reaches Kite. Status, the kill
switch, risk limits, and the promotion gate are all controlled from here.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.domain.models import Order
from app.live.broker import LiveBroker, LiveUnavailable
from app.live.controller import LiveRejected
from app.live.promotion import PromotionCriteria, evaluate_promotion
from app.live.risk import RiskLimits
from app.marketdata.instruments import BY_TOKEN
from app.state import AppState

from .deps import get_state
from .schemas import PlaceOrderIn

router = APIRouter(prefix="/live", tags=["live-trading"])


class RiskLimitsIn(BaseModel):
    max_order_value: Decimal = Field(gt=0)
    max_position_value: Decimal = Field(gt=0)
    max_daily_loss: Decimal = Field(gt=0)
    max_open_positions: int = Field(gt=0)


class EvaluateIn(BaseModel):
    report: dict


class PromoteIn(BaseModel):
    strategy_id: str
    report: dict


class LiveOrderIn(PlaceOrderIn):
    strategy_id: str | None = None


def _status(state: AppState) -> dict:
    s = state.live.status()
    s["mock_mode"] = state.settings.use_mock_market_data
    return s


@router.get("/status")
def status(state: AppState = Depends(get_state)) -> dict:
    return _status(state)


@router.get("/criteria")
def criteria() -> dict:
    """The promotion thresholds a strategy must clear before it can trade real money."""
    return PromotionCriteria().as_dict()


@router.post("/acknowledge")
def acknowledge(state: AppState = Depends(get_state)) -> dict:
    state.live.acknowledge()
    return _status(state)


@router.post("/arm")
def arm(state: AppState = Depends(get_state)) -> dict:
    try:
        state.live.arm()
    except LiveRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _status(state)


@router.post("/disarm")
def disarm(state: AppState = Depends(get_state)) -> dict:
    state.live.disarm()  # emergency stop — always allowed
    return _status(state)


@router.put("/risk")
def set_risk(payload: RiskLimitsIn, state: AppState = Depends(get_state)) -> dict:
    state.live.set_limits(
        RiskLimits(
            max_order_value=payload.max_order_value,
            max_position_value=payload.max_position_value,
            max_daily_loss=payload.max_daily_loss,
            max_open_positions=payload.max_open_positions,
        )
    )
    return _status(state)


@router.post("/evaluate")
def evaluate(payload: EvaluateIn) -> dict:
    try:
        return evaluate_promotion(payload.report).as_dict()
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"report missing field: {exc}") from exc


@router.post("/promote")
def promote(payload: PromoteIn, state: AppState = Depends(get_state)) -> dict:
    try:
        result = evaluate_promotion(payload.report)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"report missing field: {exc}") from exc
    if not result.eligible:
        # The gate refuses promotion and explains exactly which criteria failed.
        raise HTTPException(
            status_code=409,
            detail={"message": "strategy does not meet the promotion criteria", **result.as_dict()},
        )
    state.live.promote(payload.strategy_id)
    return {"promoted": payload.strategy_id, **_status(state)}


@router.delete("/promote/{strategy_id}")
def demote(strategy_id: str, state: AppState = Depends(get_state)) -> dict:
    state.live.demote(strategy_id)
    return _status(state)


@router.post("/orders")
def place_live_order(payload: LiveOrderIn, state: AppState = Depends(get_state)) -> dict:
    inst = BY_TOKEN.get(payload.instrument_token)
    order = Order(
        instrument_token=payload.instrument_token,
        side=payload.side,
        quantity=payload.quantity,
        order_type=payload.order_type,
        product=payload.product,
        limit_price=payload.limit_price,
        trigger_price=payload.trigger_price,
        tradingsymbol=inst.tradingsymbol if inst else "",
    )

    ref = payload.limit_price or payload.trigger_price
    if ref is None:
        tick = state.hub.latest(payload.instrument_token)
        ref = tick.last_price if tick else None
    if ref is None:
        raise HTTPException(status_code=422, detail="no reference price available for risk check")

    # Authorize through every gate BEFORE touching the real broker.
    try:
        state.live.authorize(order, reference_price=ref, strategy_id=payload.strategy_id)
    except LiveRejected as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        broker = LiveBroker(state.settings.kite_api_key, state.kite_access_token)
        broker_order_id = broker.place_order(order)
    except LiveUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    state.metrics.inc("live_orders_placed")
    return {"order_id": broker_order_id, "status": "submitted", "symbol": order.tradingsymbol}


@router.get("/positions")
def positions(state: AppState = Depends(get_state)) -> dict:
    try:
        broker = LiveBroker(state.settings.kite_api_key, state.kite_access_token)
        return {"positions": broker.positions()}
    except LiveUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
