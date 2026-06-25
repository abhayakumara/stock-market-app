"""Paper-trading endpoints: place orders, list orders/positions, account summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import Order
from app.marketdata.instruments import BY_TOKEN
from app.paper.engine import InsufficientFundsError
from app.state import AppState

from .deps import get_state
from .schemas import AccountOut, OrderOut, PlaceOrderIn, PositionOut

router = APIRouter(prefix="/paper", tags=["paper-trading"])


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        order_id=order.order_id,
        instrument_token=order.instrument_token,
        tradingsymbol=order.tradingsymbol,
        side=order.side,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        order_type=order.order_type,
        product=order.product,
        status=order.status.value,
        average_price=order.average_price,
        limit_price=order.limit_price,
        trigger_price=order.trigger_price,
        reject_reason=order.reject_reason,
    )


@router.post("/orders", response_model=OrderOut)
def place_order(payload: PlaceOrderIn, state: AppState = Depends(get_state)) -> OrderOut:
    instrument = BY_TOKEN.get(payload.instrument_token)
    order = Order(
        instrument_token=payload.instrument_token,
        side=payload.side,
        quantity=payload.quantity,
        order_type=payload.order_type,
        product=payload.product,
        limit_price=payload.limit_price,
        trigger_price=payload.trigger_price,
        tradingsymbol=instrument.tradingsymbol if instrument else "",
    )
    try:
        state.broker.place_order(order)
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _order_out(order)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(state: AppState = Depends(get_state)) -> list[OrderOut]:
    return [_order_out(o) for o in state.broker.orders.values()]


@router.delete("/orders/{order_id}", response_model=OrderOut)
def cancel_order(order_id: str, state: AppState = Depends(get_state)) -> OrderOut:
    if order_id not in state.broker.orders:
        raise HTTPException(status_code=404, detail="order not found")
    return _order_out(state.broker.cancel_order(order_id))


@router.get("/positions", response_model=list[PositionOut])
def list_positions(state: AppState = Depends(get_state)) -> list[PositionOut]:
    return [
        PositionOut(
            instrument_token=p.instrument_token,
            tradingsymbol=p.tradingsymbol,
            net_quantity=p.net_quantity,
            average_price=p.average_price,
            last_price=p.last_price,
            realized_pnl=p.realized_pnl,
            unrealized_pnl=p.unrealized_pnl(),
            total_charges=p.total_charges,
        )
        for p in state.broker.positions.values()
    ]


@router.get("/account", response_model=AccountOut)
def account(state: AppState = Depends(get_state)) -> AccountOut:
    s = state.broker.summary()
    return AccountOut(
        cash=s.cash,
        equity=s.equity,
        realized_pnl=s.realized_pnl,
        unrealized_pnl=s.unrealized_pnl,
        total_charges=s.total_charges,
    )
