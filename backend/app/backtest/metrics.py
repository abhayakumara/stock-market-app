"""Strategy report-card metrics computed from the equity curve and closed trades."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from app.domain.enums import Side
from app.domain.models import Trade


@dataclass(slots=True)
class ReportCard:
    initial_capital: float
    final_equity: float
    total_return_pct: float
    num_trades: int
    win_rate: float
    profit_factor: float  # gross_profit / gross_loss (math.inf if no losses)
    expectancy: float  # mean P&L per closed trade
    avg_win: float
    avg_loss: float
    max_drawdown_pct: float
    sharpe: float  # per-bar Sharpe ratio of equity returns
    total_charges: float

    def as_dict(self) -> dict:
        d = asdict(self)
        # JSON can't carry inf; surface a large sentinel the UI can render as "∞".
        if math.isinf(d["profit_factor"]):
            d["profit_factor"] = None
        return d


def trade_pnls(trades: list[Trade]) -> list[float]:
    """Closed-trade P&L (net of charges) via average-cost matching.

    Assumes the backtester always flattens before flipping direction, so every position
    segment opens from flat and closes back to flat — segments never straddle zero.
    """
    results: list[float] = []
    net = 0
    avg = 0.0
    seg_realized = 0.0
    seg_charges = 0.0
    seg_open = False

    for t in trades:
        qty = t.quantity
        price = float(t.price)
        signed = qty if t.side is Side.BUY else -qty
        if not seg_open:
            seg_open = True
            seg_realized = 0.0
            seg_charges = 0.0
        seg_charges += float(t.charges)

        if net == 0 or (net > 0) == (signed > 0):
            new_abs = abs(net) + qty
            avg = (avg * abs(net) + price * qty) / new_abs
            net += signed
        else:
            closing = min(qty, abs(net))
            direction = 1 if net > 0 else -1
            seg_realized += (price - avg) * closing * direction
            net += signed
            if net == 0:
                avg = 0.0

        if net == 0 and seg_open:
            results.append(seg_realized - seg_charges)
            seg_open = False
    return results


def _max_drawdown_pct(equity: list[float]) -> float:
    peak = -math.inf
    max_dd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)
    return max_dd * 100.0


def _sharpe(equity: list[float]) -> float:
    if len(equity) < 3:
        return 0.0
    returns = [
        (equity[i] / equity[i - 1] - 1.0)
        for i in range(1, len(equity))
        if equity[i - 1] != 0
    ]
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    sd = math.sqrt(var)
    return (mean / sd) if sd > 0 else 0.0


def build_report(
    *, initial_capital: float, equity_curve: list[float], trades: list[Trade], total_charges: float
) -> ReportCard:
    pnls = trade_pnls(trades)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    final_equity = equity_curve[-1] if equity_curve else initial_capital

    return ReportCard(
        initial_capital=round(initial_capital, 2),
        final_equity=round(final_equity, 2),
        total_return_pct=round((final_equity / initial_capital - 1.0) * 100.0, 2)
        if initial_capital
        else 0.0,
        num_trades=len(pnls),
        win_rate=round(len(wins) / len(pnls) * 100.0, 2) if pnls else 0.0,
        profit_factor=round(gross_profit / gross_loss, 2) if gross_loss > 0 else math.inf,
        expectancy=round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
        avg_win=round(sum(wins) / len(wins), 2) if wins else 0.0,
        avg_loss=round(sum(losses) / len(losses), 2) if losses else 0.0,
        max_drawdown_pct=round(_max_drawdown_pct(equity_curve), 2),
        sharpe=round(_sharpe(equity_curve), 4),
        total_charges=round(total_charges, 2),
    )
