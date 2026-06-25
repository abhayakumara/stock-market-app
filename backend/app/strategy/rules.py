"""Config-driven rule strategy.

A strategy is expressed as JSON-ish config so it can be authored in the UI or generated
by Claude from natural language, with no Python required:

    {
      "name": "SMA 20/50 crossover",
      "indicators": {
        "fast": {"kind": "sma", "period": 20},
        "slow": {"kind": "sma", "period": 50}
      },
      "entry_long": [{"left": "fast", "op": ">", "right": "slow"}],
      "exit_long":  [{"left": "fast", "op": "<", "right": "slow"}],
      "allow_short": false
    }

Operands (``left`` / ``right``) are either an indicator name, the special source
``"close"``/``"price"``, or a number. Each rule list is an AND of its conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.analysis import indicators as ind
from app.analysis.candles import Candle, closes

from .base import Signal

_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


def _build_indicator(spec: dict, source: list[float]) -> ind.Series:
    kind = spec["kind"]
    period = int(spec.get("period", 14))
    if kind == "sma":
        return ind.sma(source, period)
    if kind == "ema":
        return ind.ema(source, period)
    if kind == "rsi":
        return ind.rsi(source, period)
    if kind == "macd":
        return ind.macd(source, spec.get("fast", 12), spec.get("slow", 26),
                        spec.get("signal", 9))[0]
    if kind == "macd_signal":
        return ind.macd(source, spec.get("fast", 12), spec.get("slow", 26),
                        spec.get("signal", 9))[1]
    if kind in ("boll_upper", "boll_mid", "boll_lower"):
        mid, upper, lower = ind.bollinger(source, spec.get("period", 20), spec.get("mult", 2.0))
        return {"boll_upper": upper, "boll_mid": mid, "boll_lower": lower}[kind]
    raise ValueError(f"unknown indicator kind: {kind}")


@dataclass
class RuleStrategy:
    name: str
    config: dict[str, Any]
    allow_short: bool = field(default=False)

    def __post_init__(self) -> None:
        self.allow_short = bool(self.config.get("allow_short", False))

    def _series(self, candles: list[Candle]) -> dict[str, ind.Series]:
        src = closes(candles)
        out: dict[str, ind.Series] = {}
        for name, spec in self.config.get("indicators", {}).items():
            out[name] = _build_indicator(spec, src)
        return out

    def _operand(self, token: Any, series: dict[str, ind.Series], i: int) -> float | None:
        if isinstance(token, (int, float)):
            return float(token)
        if token in ("close", "price"):
            return self._close_i
        s = series.get(token)
        return None if s is None else s[i]

    def _all_true(self, rules: list[dict], series: dict[str, ind.Series], i: int) -> bool:
        for rule in rules:
            left = self._operand(rule["left"], series, i)
            right = self._operand(rule["right"], series, i)
            if left is None or right is None:
                return False
            if not _OPS[rule["op"]](left, right):
                return False
        return bool(rules)

    def signal(self, candles: list[Candle], position: int) -> Signal:
        if not candles:
            return Signal.FLAT
        series = self._series(candles)
        i = len(candles) - 1
        self._close_i = candles[i].close

        if position == 0:
            if self._all_true(self.config.get("entry_long", []), series, i):
                return Signal.LONG
            if self.allow_short and self._all_true(self.config.get("entry_short", []), series, i):
                return Signal.SHORT
            return Signal.FLAT
        if position > 0:
            if self._all_true(self.config.get("exit_long", []), series, i):
                return Signal.FLAT
            return Signal.LONG
        # position < 0 (short)
        if self._all_true(self.config.get("exit_short", []), series, i):
            return Signal.FLAT
        return Signal.SHORT


def build_strategy(config: dict[str, Any]) -> RuleStrategy:
    """Construct a :class:`RuleStrategy` from a config dict (validates required keys)."""
    if "indicators" not in config or not isinstance(config["indicators"], dict):
        raise ValueError("config must include an 'indicators' object")
    if not config.get("entry_long") and not config.get("entry_short"):
        raise ValueError("config must include at least one entry rule")
    return RuleStrategy(name=config.get("name", "custom"), config=config)
