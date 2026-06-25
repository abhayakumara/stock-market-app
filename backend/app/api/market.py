"""Market-data endpoints: REST quote + a WebSocket tick stream for the frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.state import AppState

from .deps import get_state

router = APIRouter(tags=["market-data"])


@router.get("/quote/{instrument_token}")
def quote(instrument_token: int, state: AppState = Depends(get_state)) -> dict:
    tick = state.hub.latest(instrument_token)
    if tick is None:
        return {"instrument_token": instrument_token, "last_price": None}
    return {
        "instrument_token": instrument_token,
        "last_price": str(tick.last_price),
        "bid": str(tick.bid) if tick.bid is not None else None,
        "ask": str(tick.ask) if tick.ask is not None else None,
        "timestamp": tick.timestamp.isoformat(),
    }


@router.websocket("/ws/ticks")
async def ws_ticks(websocket: WebSocket) -> None:
    state: AppState = websocket.app.state.appstate
    await websocket.accept()
    try:
        async for tick in state.hub.subscribe():
            await websocket.send_json(
                {
                    "instrument_token": tick.instrument_token,
                    "last_price": str(tick.last_price),
                    "bid": str(tick.bid) if tick.bid is not None else None,
                    "ask": str(tick.ask) if tick.ask is not None else None,
                    "timestamp": tick.timestamp.isoformat(),
                }
            )
    except WebSocketDisconnect:
        pass
