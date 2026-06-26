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
    # --- Beginner-friendly presets (plain-English) ---------------------------------
    "price_above_average": {
        "name": "Ride the trend (price above its average)",
        "description": (
            "Buy when the price is above its own average of the last 50 bars, which "
            "usually means it's in an up-trend. Sell when it slips back below the "
            "average. Simple way to stay in while things are going up and step aside "
            "when they turn down."
        ),
        "indicators": {"average": {"kind": "sma", "period": 50}},
        "entry_long": [{"left": "close", "op": ">", "right": "average"}],
        "exit_long": [{"left": "close", "op": "<", "right": "average"}],
        "allow_short": False,
    },
    "ema_crossover": {
        "name": "Fast vs slow average (quick trend change)",
        "description": (
            "Watches a fast average (last 12 bars) and a slow one (last 26 bars). "
            "When the fast average rises above the slow one, the recent mood is turning "
            "up, so buy. When it drops back below, sell. Reacts a bit quicker than the "
            "plain 20/50 crossover."
        ),
        "indicators": {
            "fast": {"kind": "ema", "period": 12},
            "slow": {"kind": "ema", "period": 26},
        },
        "entry_long": [{"left": "fast", "op": ">", "right": "slow"}],
        "exit_long": [{"left": "fast", "op": "<", "right": "slow"}],
        "allow_short": False,
    },
    "volume_breakout": {
        "name": "Big-volume push (crowd is buying)",
        "description": (
            "Buy only when two things happen together: a lot more shares than usual "
            "change hands (today's volume is over twice the recent average) AND the "
            "price is above its short-term average, i.e. moving up. Heavy volume behind "
            "a rising price means real interest, not a random wiggle. Sell when the "
            "price falls back below its short-term average."
        ),
        "indicators": {
            "vol_threshold": {"kind": "vol_sma", "period": 20, "mult": 2.0},
            "trend": {"kind": "sma", "period": 10},
        },
        "entry_long": [
            {"left": "volume", "op": ">", "right": "vol_threshold"},
            {"left": "close", "op": ">", "right": "trend"},
        ],
        "exit_long": [{"left": "close", "op": "<", "right": "trend"}],
        "allow_short": False,
    },
    "vwap_trend": {
        "name": "Above the fair price (VWAP)",
        "description": (
            "VWAP is the average price weighted by how many shares traded at each "
            "level, so it's a good 'fair value' for the day. When the price is above "
            "VWAP, buyers are in control, so buy. When it drops below VWAP, step out. "
            "Popular with intraday traders."
        ),
        "indicators": {"vwap": {"kind": "vwap"}},
        "entry_long": [{"left": "close", "op": ">", "right": "vwap"}],
        "exit_long": [{"left": "close", "op": "<", "right": "vwap"}],
        "allow_short": False,
    },
    "breakout_high": {
        "name": "New-high breakout (price escapes its range)",
        "description": (
            "Buy when the price climbs above the highest point of the last 20 bars — "
            "it has broken out of its recent range to a new high, which can kick off a "
            "fresh move up. Get out if it sinks below the lowest point of the last 10 "
            "bars, meaning the breakout failed."
        ),
        "indicators": {
            "range_high": {"kind": "highest", "period": 20},
            "range_low": {"kind": "lowest", "period": 10},
        },
        "entry_long": [{"left": "close", "op": ">", "right": "range_high"}],
        "exit_long": [{"left": "close", "op": "<", "right": "range_low"}],
        "allow_short": False,
    },
}


def list_templates() -> list[dict[str, Any]]:
    return [
        {"id": key, "name": cfg["name"], "description": cfg["description"], "config": cfg}
        for key, cfg in TEMPLATES.items()
    ]
