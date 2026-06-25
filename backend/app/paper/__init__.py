"""In-house paper-trading engine.

Zerodha provides no sandbox/paper API, so this package simulates order fills against
the live tick feed and models real brokerage + statutory charges. The same engine is
designed to be reused by the backtester so paper and backtest results stay consistent.
"""

from .charges import ChargesModel
from .engine import PaperBroker

__all__ = ["ChargesModel", "PaperBroker"]
