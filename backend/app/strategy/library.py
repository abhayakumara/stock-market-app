"""Built-in strategy templates.

Each template is a plain config dict consumable by :func:`build_strategy`. They double as
worked examples for the AI strategy author (few-shot) and as one-click presets in the UI.
"""

from __future__ import annotations

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "sma_crossover": {
        "name": "SMA 20/50 crossover",
        "description": "Go long when the fast SMA is above the slow SMA; exit when it falls below.",
        "indicators": {
            "fast": {"kind": "sma", "period": 20},
            "slow": {"kind": "sma", "period": 50},
        },
        "entry_long": [{"left": "fast", "op": ">", "right": "slow"}],
        "exit_long": [{"left": "fast", "op": "<", "right": "slow"}],
        "allow_short": False,
    },
    "rsi_reversion": {
        "name": "RSI(14) mean reversion",
        "description": "Buy oversold (RSI < 30), exit when RSI recovers above 50.",
        "indicators": {"rsi": {"kind": "rsi", "period": 14}},
        "entry_long": [{"left": "rsi", "op": "<", "right": 30}],
        "exit_long": [{"left": "rsi", "op": ">", "right": 50}],
        "allow_short": False,
    },
    "macd_trend": {
        "name": "MACD trend",
        "description": "Long while the MACD line is above its signal line.",
        "indicators": {
            "macd": {"kind": "macd"},
            "macd_signal": {"kind": "macd_signal"},
        },
        "entry_long": [{"left": "macd", "op": ">", "right": "macd_signal"}],
        "exit_long": [{"left": "macd", "op": "<", "right": "macd_signal"}],
        "allow_short": False,
    },
    "bollinger_reversion": {
        "name": "Bollinger reversion",
        "description": "Buy when price closes below the lower band; exit at the middle band.",
        "indicators": {
            "lower": {"kind": "boll_lower", "period": 20, "mult": 2.0},
            "mid": {"kind": "boll_mid", "period": 20},
        },
        "entry_long": [{"left": "close", "op": "<", "right": "lower"}],
        "exit_long": [{"left": "close", "op": ">", "right": "mid"}],
        "allow_short": False,
    },
}


def list_templates() -> list[dict[str, Any]]:
    return [
        {"id": key, "name": cfg["name"], "description": cfg["description"], "config": cfg}
        for key, cfg in TEMPLATES.items()
    ]
