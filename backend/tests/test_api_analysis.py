"""API tests for the Phase 2/3 endpoints: analysis, screener, strategy, backtest, AI."""

from fastapi.testclient import TestClient

from app.api.deps import get_state
from app.config import Settings, get_settings
from app.main import create_app
from app.state import AppState

TOKEN = 738561  # RELIANCE in the seed set


def build_client():
    app = create_app()
    settings = Settings(use_mock_market_data=True, anthropic_api_key="")
    state = AppState(settings)
    app.dependency_overrides[get_state] = lambda: state
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), state


def test_candles_endpoint_returns_requested_count():
    client, _ = build_client()
    resp = client.get(f"/analysis/candles/{TOKEN}?count=120&interval_minutes=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["candles"]) == 120
    first = data["candles"][0]
    assert {"open", "high", "low", "close", "volume", "timestamp"} <= first.keys()


def test_indicators_endpoint_aligns_series_with_close():
    client, _ = build_client()
    data = client.get(f"/analysis/indicators/{TOKEN}?count=120").json()
    n = len(data["close"])
    for key in ("sma20", "sma50", "rsi14", "macd", "boll_upper"):
        assert len(data[key]) == n


def test_screener_returns_structure():
    client, _ = build_client()
    data = client.get("/analysis/screener?scan=rsi_oversold").json()
    assert data["scan"] == "rsi_oversold"
    assert "hits" in data
    assert "rsi_oversold" in data["available_scans"]


def test_unknown_scan_400():
    client, _ = build_client()
    assert client.get("/analysis/screener?scan=nope").status_code == 400


def test_strategy_templates_listed():
    client, _ = build_client()
    data = client.get("/strategy/templates").json()
    ids = {t["id"] for t in data["templates"]}
    assert "sma_crossover" in ids
    assert "rsi_reversion" in ids


def test_backtest_with_template_runs():
    client, _ = build_client()
    resp = client.post(
        "/strategy/backtest",
        json={
            "instrument_token": TOKEN,
            "template": "sma_crossover",
            "quantity": 10,
            "candle_count": 300,
            "warmup": 50,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "report" in body
    assert len(body["equity_curve"]) == 300
    assert "total_return_pct" in body["report"]


def test_backtest_custom_config_validation_error():
    client, _ = build_client()
    resp = client.post(
        "/strategy/backtest",
        json={"instrument_token": TOKEN, "config": {"indicators": {}}},
    )
    assert resp.status_code == 422


def test_backtest_requires_template_or_config():
    client, _ = build_client()
    resp = client.post("/strategy/backtest", json={"instrument_token": TOKEN})
    assert resp.status_code == 422


def test_save_and_list_strategy():
    client, _ = build_client()
    cfg = {
        "name": "my rsi",
        "indicators": {"rsi": {"kind": "rsi", "period": 14}},
        "entry_long": [{"left": "rsi", "op": "<", "right": 25}],
        "exit_long": [{"left": "rsi", "op": ">", "right": 55}],
    }
    assert client.post("/strategy/saved", json={"name": "my rsi", "config": cfg}).status_code == 200
    listed = client.get("/strategy/saved").json()
    assert any(s["name"] == "my rsi" for s in listed["strategies"])


def test_ai_commentary_503_without_key():
    client, _ = build_client()
    # No ANTHROPIC_API_KEY configured → graceful 503.
    assert client.get(f"/ai/commentary/{TOKEN}").status_code == 503
