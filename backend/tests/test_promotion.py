from app.live.promotion import PromotionCriteria, evaluate_promotion


def good_report(**overrides):
    report = {
        "num_trades": 40,
        "win_rate": 60.0,
        "max_drawdown_pct": 10.0,
        "total_return_pct": 12.0,
        "profit_factor": 1.8,
        "sharpe": 0.05,
    }
    report.update(overrides)
    return report


def test_strong_strategy_is_eligible():
    result = evaluate_promotion(good_report())
    assert result.eligible
    assert all(c.passed for c in result.checks)


def test_too_few_trades_blocks():
    result = evaluate_promotion(good_report(num_trades=5))
    assert not result.eligible
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "Minimum trades" for c in failed)


def test_drawdown_too_large_blocks():
    result = evaluate_promotion(good_report(max_drawdown_pct=35.0))
    assert not result.eligible
    assert any(c.name == "Max drawdown" and not c.passed for c in result.checks)


def test_negative_return_blocks():
    result = evaluate_promotion(good_report(total_return_pct=-3.0))
    assert not result.eligible


def test_infinite_profit_factor_passes():
    # No losing trades → profit_factor None (infinite); should pass that check.
    result = evaluate_promotion(good_report(profit_factor=None))
    pf_check = next(c for c in result.checks if c.name == "Profit factor")
    assert pf_check.passed


def test_custom_criteria_are_respected():
    strict = PromotionCriteria(min_trades=100)
    result = evaluate_promotion(good_report(num_trades=40), strict)
    assert not result.eligible
