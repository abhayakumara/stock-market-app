"""API tests for Phase 4/5 endpoints (live gate, alerts, journal, metrics)."""

from fastapi.testclient import TestClient

from app.api.deps import get_state
from app.config import Settings, get_settings
from app.main import create_app
from app.state import AppState

TOKEN = 738561


def build_client():
    app = create_app()
    settings = Settings(use_mock_market_data=True, anthropic_api_key="")
    state = AppState(settings)
    app.dependency_overrides[get_state] = lambda: state
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), state


# ---- live gate ----------------------------------------------------------------
def test_live_status_defaults_safe():
    client, _ = build_client()
    s = client.get("/live/status").json()
    assert s["configured"] is False
    assert s["armed"] is False
    assert s["acknowledged"] is False


def test_cannot_arm_when_unconfigured():
    client, _ = build_client()
    resp = client.post("/live/arm")
    assert resp.status_code == 400  # not configured


def test_arm_requires_ack_then_succeeds_when_configured():
    client, state = build_client()
    state.live.configured = True  # simulate a completed Kite login
    assert client.post("/live/arm").status_code == 400  # not acknowledged yet
    client.post("/live/acknowledge")
    armed = client.post("/live/arm").json()
    assert armed["armed"] is True


def test_live_order_blocked_when_disarmed():
    client, _ = build_client()
    resp = client.post(
        "/live/orders",
        json={"instrument_token": TOKEN, "side": "BUY", "quantity": 1, "order_type": "LIMIT",
              "product": "CNC", "limit_price": 100},
    )
    assert resp.status_code == 409  # rejected by the live gate (not configured/armed)


def test_promotion_rejects_weak_strategy():
    client, _ = build_client()
    weak = {
        "num_trades": 3, "win_rate": 20.0, "max_drawdown_pct": 40.0,
        "total_return_pct": -5.0, "profit_factor": 0.5, "sharpe": -0.1,
    }
    resp = client.post("/live/promote", json={"strategy_id": "x", "report": weak})
    assert resp.status_code == 409
    assert "checks" in resp.json()["detail"]


def test_promotion_accepts_strong_strategy_then_listed():
    client, _ = build_client()
    strong = {
        "num_trades": 40, "win_rate": 60.0, "max_drawdown_pct": 8.0,
        "total_return_pct": 15.0, "profit_factor": 1.9, "sharpe": 0.05,
    }
    resp = client.post("/live/promote", json={"strategy_id": "sma_crossover", "report": strong})
    assert resp.status_code == 200
    assert "sma_crossover" in resp.json()["promoted"]


def test_evaluate_returns_checklist():
    client, _ = build_client()
    report = {
        "num_trades": 40, "win_rate": 60.0, "max_drawdown_pct": 8.0,
        "total_return_pct": 15.0, "profit_factor": 1.9, "sharpe": 0.05,
    }
    data = client.post("/live/evaluate", json={"report": report}).json()
    assert data["eligible"] is True
    assert len(data["checks"]) == 6


def test_set_risk_limits():
    client, _ = build_client()
    resp = client.put(
        "/live/risk",
        json={"max_order_value": 2000, "max_position_value": 5000,
              "max_daily_loss": 1000, "max_open_positions": 3},
    )
    assert resp.status_code == 200
    assert resp.json()["limits"]["max_order_value"] == "2000"


# ---- alerts -------------------------------------------------------------------
def test_alert_crud():
    client, _ = build_client()
    created = client.post(
        "/alerts", json={"instrument_token": TOKEN, "op": ">", "price": 3000, "note": "watch"}
    ).json()
    assert created["active"] is True
    listed = client.get("/alerts").json()
    assert len(listed["alerts"]) == 1
    assert client.delete(f"/alerts/{created['id']}").status_code == 200
    assert client.get("/alerts").json()["alerts"] == []


# ---- journal ------------------------------------------------------------------
def test_journal_add_and_list():
    client, _ = build_client()
    client.post("/journal", json={"text": "Cut a loss early, good discipline.", "tags": ["risk"]})
    entries = client.get("/journal").json()["entries"]
    assert len(entries) == 1
    assert entries[0]["tags"] == ["risk"]


# ---- AI guards ----------------------------------------------------------------
def test_ai_coach_503_without_key():
    client, _ = build_client()
    assert client.get("/ai/coach").status_code == 503


# ---- metrics ------------------------------------------------------------------
def test_metrics_endpoint():
    client, _ = build_client()
    data = client.get("/metrics").json()
    assert "counters" in data
    assert "uptime_seconds" in data
