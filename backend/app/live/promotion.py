"""The promotion gate: decide whether a strategy has *earned* real money.

A strategy may only be promoted to live trading after its track record (a backtest today,
and accumulated paper results later) clears every criterion below. The evaluator returns a
per-criterion checklist so the UI can show exactly what passed and what didn't.

These thresholds are intentionally demanding. Passing them is **not** a guarantee of
future profit — see docs/RISKS.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromotionCriteria:
    min_trades: int = 30
    min_win_rate: float = 50.0  # %
    max_drawdown: float = 20.0  # % (lower is better)
    min_total_return: float = 5.0  # %
    min_profit_factor: float = 1.3
    min_sharpe: float = 0.0  # per-bar Sharpe must be positive

    def as_dict(self) -> dict:
        return {
            "min_trades": self.min_trades,
            "min_win_rate": self.min_win_rate,
            "max_drawdown": self.max_drawdown,
            "min_total_return": self.min_total_return,
            "min_profit_factor": self.min_profit_factor,
            "min_sharpe": self.min_sharpe,
        }


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    actual: float | None
    threshold: float
    detail: str


@dataclass(frozen=True, slots=True)
class PromotionResult:
    eligible: bool
    checks: list[Check]

    def as_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "actual": c.actual,
                    "threshold": c.threshold,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


def evaluate_promotion(report: dict, criteria: PromotionCriteria | None = None) -> PromotionResult:
    """Evaluate a backtest/paper ``ReportCard`` dict against the promotion criteria."""
    c = criteria or PromotionCriteria()
    # profit_factor may be None (no losing trades → infinite); treat as passing.
    pf = report.get("profit_factor")
    pf_actual = pf if pf is not None else float("inf")

    checks = [
        Check(
            "Minimum trades",
            report["num_trades"] >= c.min_trades,
            float(report["num_trades"]),
            float(c.min_trades),
            f"At least {c.min_trades} closed trades for statistical significance.",
        ),
        Check(
            "Win rate",
            report["win_rate"] >= c.min_win_rate,
            report["win_rate"],
            c.min_win_rate,
            f"Win rate ≥ {c.min_win_rate}%.",
        ),
        Check(
            "Max drawdown",
            report["max_drawdown_pct"] <= c.max_drawdown,
            report["max_drawdown_pct"],
            c.max_drawdown,
            f"Peak-to-trough drawdown ≤ {c.max_drawdown}%.",
        ),
        Check(
            "Total return",
            report["total_return_pct"] >= c.min_total_return,
            report["total_return_pct"],
            c.min_total_return,
            f"Net return ≥ {c.min_total_return}% after costs.",
        ),
        Check(
            "Profit factor",
            pf_actual >= c.min_profit_factor,
            None if pf is None else pf,
            c.min_profit_factor,
            f"Gross profit / gross loss ≥ {c.min_profit_factor}.",
        ),
        Check(
            "Sharpe (per bar)",
            report["sharpe"] > c.min_sharpe,
            report["sharpe"],
            c.min_sharpe,
            "Risk-adjusted return must be positive.",
        ),
    ]
    return PromotionResult(eligible=all(ch.passed for ch in checks), checks=checks)
