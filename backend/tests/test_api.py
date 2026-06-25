"""API integration tests.

Drives the routers with a controlled AppState (hub not started) so fills are
deterministic: we feed ticks directly into the broker via the hub's on_tick wiring.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_state
from app.config import Settings
from app.domain.models import Tick
from app.main import create_app
from app.state import AppState

TOKEN = 738561  # RELIANCE in the seed set


def build_client():
    app = create_app()
    state = AppState(Settings(use_mock_market_data=True))  # hub built but not started
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app), state


def test_list_instruments():
    client, _ = build_client()
    resp = client.get("/instruments")
    assert resp.status_code == 200
    symbols = {i["tradingsymbol"] for i in resp.json()}
    assert "RELIANCE" in symbols


def test_place_paper_order_fills_on_tick_and_updates_positions():
    client, state = build_client()

    # Order rests (no price yet).
    resp = client.post(
        "/paper/orders",
        json={"instrument_token": TOKEN, "side": "BUY", "quantity": 5, "order_type": "MARKET"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPEN"

    # Simulate a market tick through the same wiring the hub uses.
    state.hub.on_tick(Tick(TOKEN, Decimal("2900")))

    positions = client.get("/paper/positions").json()
    assert len(positions) == 1
    assert positions[0]["net_quantity"] == 5

    account = client.get("/paper/account").json()
    assert Decimal(account["cash"]) < Decimal("1000000")  # cash spent on the buy


def test_insufficient_funds_returns_400():
    client, state = build_client()
    state.hub.on_tick(Tick(TOKEN, Decimal("2900")))  # establish a price
    resp = client.post(
        "/paper/orders",
        json={
            "instrument_token": TOKEN,
            "side": "BUY",
            "quantity": 100000,  # ~29 crore notional, far beyond capital
            "order_type": "MARKET",
            "product": "CNC",
        },
    )
    assert resp.status_code == 400


def test_health_reports_mock_mode():
    client, _ = build_client()
    assert client.get("/health").json()["mode"] == "mock"
