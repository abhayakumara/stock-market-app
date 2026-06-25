"""FastAPI application entrypoint.

Wires the market hub (feeding the paper broker) into the app lifespan and mounts the
REST + WebSocket routers.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, instruments, market, trading
from app.config import get_settings
from app.state import AppState


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    state = AppState(settings)
    app.state.appstate = state
    await state.start()
    try:
        yield
    finally:
        await state.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Trading App", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        live = settings.kite_configured and not settings.use_mock_market_data
        return {"status": "ok", "mode": "live" if live else "mock"}

    app.include_router(auth.router)
    app.include_router(instruments.router)
    app.include_router(trading.router)
    app.include_router(market.router)
    return app


app = create_app()
