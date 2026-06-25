"""Event-driven backtester.

Replays historical candles through the **same** :class:`~app.paper.engine.PaperBroker`
and :class:`~app.paper.charges.ChargesModel` used for live paper trading, so backtest and
paper results stay consistent (the plan's paper↔backtest parity requirement).
"""

from .engine import BacktestResult, run_backtest
from .metrics import ReportCard, build_report

__all__ = ["run_backtest", "BacktestResult", "build_report", "ReportCard"]
