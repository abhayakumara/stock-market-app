"""Real-money trading: the strict promotion gate, risk controls, and live order service.

Every real order must pass, in order:
  1. configured  — Kite keys present and a daily access token obtained,
  2. acknowledged — the user has accepted the real-money risk disclosure,
  3. armed        — the global kill switch is ON (default OFF),
  4. promoted     — strategy-driven orders require a promoted strategy,
  5. risk-checked — per-order / per-position / daily-loss / open-position caps.

If any check fails the order is rejected with an explicit, human-readable reason.
"""

from .broker import LiveBroker, LiveUnavailable
from .controller import LiveController, LiveRejected
from .promotion import PromotionCriteria, evaluate_promotion
from .risk import RiskDecision, RiskLimits, RiskManager

__all__ = [
    "LiveBroker",
    "LiveUnavailable",
    "LiveController",
    "LiveRejected",
    "PromotionCriteria",
    "evaluate_promotion",
    "RiskDecision",
    "RiskLimits",
    "RiskManager",
]
