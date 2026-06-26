from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.analysis.candles import Candle
from app.backtest import run_backtest
from app.backtest.metrics import trade_pnls
from app.domain.enums import Side
from app.domain.models import Trade
from app.strategy import build_strategy
from app.strategy.library import TEMPLATES

TOKEN = 738561


def _candles_from_closes(values: list[float]) -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    out = []
    for i, c in enumerate(values):
        out.append(Candle(base + timedelta(minutes=5 * i), c, c, c, c, 1000))
    return out


def test_trade_pnls_simple_round_trip():
    trades = [
        Trade("1", TOKEN, Side.BUY, 10, Decimal("100"), Decimal("0")),
        Trade("2", TOKEN, Side.SELL, 10, Decimal("110"), Decimal("0")),
    ]
    assert trade_pnls(trades) == [100.0]


def test_trade_pnls_nets_charges():
    trades = [
        Trade("1", TOKEN, Side.BUY, 10, Decimal("100"), Decimal("5")),
        Trade("2", TOKEN, Side.SELL, 10, Decimal("110"), Decimal("5")),
    ]
    assert trade_pnls(trades) == [90.0]  # 100 gross - 10 charges


def test_sma_crossover_backtest_runs_and_reports():
    strat = build_strategy(TEMPLATES["sma_crossover"])
    # An up-then-down ramp so the fast/slow crossover both enters and exits.
    closes = [float(x) for x in range(100, 200)] + [float(x) for x in range(200, 100, -1)]
    candles = _candles_from_closes(closes)
    result = run_backtest(
        candles=candles,
        strategy=strat,
        instrument_token=TOKEN,
        quantity=10,
        warmup=50,
    )
    assert result.report.num_trades >= 1
    assert len(result.equity_curve) == len(candles)
    # The uptrend should have produced a profitable long round trip overall.
    assert result.report.total_return_pct != 0.0


def test_profitable_long_trend_has_positive_return():
    # Strictly rising market; SMA crossover stays long and profits.
    strat = build_strategy(TEMPLATES["sma_crossover"])
    closes = [100.0 + i * 0.5 for i in range(160)]
    candles = _candles_from_closes(closes)
    result = run_backtest(
        candles=candles, strategy=strat, instrument_token=TOKEN, quantity=100, warmup=50
    )
    assert result.report.total_return_pct > 0
    assert result.report.max_drawdown_pct >= 0


def test_no_entry_rules_rejected():
    import pytest

    with pytest.raises(ValueError):
        build_strategy({"indicators": {"x": {"kind": "sma", "period": 5}}})


def test_rsi_reversion_template_builds():
    strat = build_strategy(TEMPLATES["rsi_reversion"])
    candles = _candles_from_closes([100 - i for i in range(30)] + [70 + i for i in range(30)])
    result = run_backtest(
        candles=candles, strategy=strat, instrument_token=TOKEN, quantity=10, warmup=20
    )
    assert len(result.equity_curve) == len(candles)


def _ohlcv_candles(rows: list[tuple[float, float, float, float, float]]) -> list[Candle]:
    """Build candles from (open, high, low, close, volume) tuples."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(base + timedelta(minutes=5 * i), o, h, low, c, v)
        for i, (o, h, low, c, v) in enumerate(rows)
    ]


def test_all_templates_backtest_without_error():
    # A rising series with realistic high/low/volume so every template can compute.
    rows = []
    for i in range(160):
        close = 100.0 + i * 0.5
        rows.append((close - 0.2, close + 0.5, close - 0.5, close, 1000.0 + i))
    candles = _ohlcv_candles(rows)
    for name, cfg in TEMPLATES.items():
        strat = build_strategy(cfg)
        result = run_backtest(
            candles=candles, strategy=strat, instrument_token=TOKEN, quantity=10, warmup=55
        )
        assert len(result.equity_curve) == len(candles), name


def test_volume_breakout_enters_on_volume_spike():
    # Flat-ish rising price with a normal volume baseline, then one bar with 3x volume
    # while price is above its short average -> the strategy should take a long.
    rows = [(100.0, 100.5, 99.5, 100.0 + i * 0.1, 1000.0) for i in range(40)]
    rows.append((104.0, 105.0, 103.9, 104.5, 5000.0))  # volume spike on a rising close
    rows += [(104.5, 105.0, 104.0, 104.5 + i * 0.1, 1000.0) for i in range(20)]
    candles = _ohlcv_candles(rows)
    strat = build_strategy(TEMPLATES["volume_breakout"])
    result = run_backtest(
        candles=candles, strategy=strat, instrument_token=TOKEN, quantity=10, warmup=25
    )
    # At least one entry fill happened (the position may still be open at the end).
    assert any(t["side"] == "BUY" for t in result.trades)


def test_breakout_high_enters_on_new_high():
    # 30 bars stuck in a tight range, then a clear break above the range high.
    rows = [(100.0, 101.0, 99.0, 100.0, 1000.0) for _ in range(30)]
    rows.append((101.0, 105.0, 100.5, 104.0, 1000.0))  # close above the prior 20-bar high
    rows += [(104.0, 105.0, 103.0, 104.0, 1000.0) for _ in range(20)]
    candles = _ohlcv_candles(rows)
    strat = build_strategy(TEMPLATES["breakout_high"])
    result = run_backtest(
        candles=candles, strategy=strat, instrument_token=TOKEN, quantity=10, warmup=25
    )
    assert any(t["side"] == "BUY" for t in result.trades)
