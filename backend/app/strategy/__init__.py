"""Trading strategies and a config-driven rule DSL.

A strategy maps candle history + current position to a target :class:`Signal`
(``LONG`` / ``FLAT`` / ``SHORT``). The same strategy object is consumed by the
backtester today and by the live paper/real loop in later phases, so signal logic is
written once and reused across modes.
"""

from .base import Signal, Strategy
from .library import TEMPLATES, list_templates
from .rules import RuleStrategy, build_strategy

__all__ = [
    "Signal",
    "Strategy",
    "RuleStrategy",
    "build_strategy",
    "TEMPLATES",
    "list_templates",
]
