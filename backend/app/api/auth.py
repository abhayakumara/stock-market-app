"""Kite Connect login endpoints.

These only work once ``KITE_API_KEY`` / ``KITE_API_SECRET`` are configured and the
``kiteconnect`` extra is installed. They drive the daily interactive login that yields an
access token. Token persistence (encrypted, per user) is added in a later phase; for now
the access token is held in process state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.integrations.kite import KiteAuth
from app.state import AppState

from .deps import get_state

router = APIRouter(prefix="/auth/kite", tags=["auth"])


@router.get("/login")
def login(settings: Settings = Depends(get_settings)) -> dict:
    if not settings.kite_configured:
        raise HTTPException(status_code=503, detail="Kite API keys not configured")
    try:
        url = KiteAuth(settings.kite_api_key, settings.kite_api_secret).login_url()
    except ImportError as exc:
        raise HTTPException(
            status_code=503, detail="kiteconnect not installed (pip install trading-backend[kite])"
        ) from exc
    return {"login_url": url}


@router.get("/callback")
def callback(
    request_token: str,
    settings: Settings = Depends(get_settings),
    state: AppState = Depends(get_state),
) -> dict:
    if not settings.kite_configured:
        raise HTTPException(status_code=503, detail="Kite API keys not configured")
    try:
        session = KiteAuth(settings.kite_api_key, settings.kite_api_secret).exchange_request_token(
            request_token
        )
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="kiteconnect not installed") from exc
    # Store the daily token in memory; this also flips live.configured = True (kill
    # switch still defaults OFF). NOTE: encrypt + persist per the plan in a later phase.
    state.set_kite_access_token(session.access_token)
    return {"user_id": session.user_id, "user_name": session.user_name, "connected": True}
