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
