"""Price alert endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.alerts import Alert
from app.marketdata.instruments import BY_TOKEN
from app.state import AppState

from .deps import get_state

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertIn(BaseModel):
    instrument_token: int
    op: Literal[">", "<"]
    price: Decimal
    note: str = ""


@router.get("")
def list_alerts(state: AppState = Depends(get_state)) -> dict:
    return {
        "alerts": [a.as_dict() for a in state.alerts.list()],
        "triggered": [a.as_dict() for a in state.triggered_alerts],
    }


@router.post("")
def add_alert(payload: AlertIn, state: AppState = Depends(get_state)) -> dict:
    inst = BY_TOKEN.get(payload.instrument_token)
    alert = state.alerts.add(
        Alert(
            instrument_token=payload.instrument_token,
            op=payload.op,
            price=payload.price,
            tradingsymbol=inst.tradingsymbol if inst else "",
            note=payload.note,
        )
    )
    return alert.as_dict()


@router.delete("/{alert_id}")
def remove_alert(alert_id: int, state: AppState = Depends(get_state)) -> dict:
    if not state.alerts.remove(alert_id):
        raise HTTPException(status_code=404, detail="alert not found")
    return {"removed": alert_id}
