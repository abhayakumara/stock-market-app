"""Claude client wrapper for market commentary and strategy authoring.

Uses the official Anthropic SDK with model ``claude-opus-4-8`` and adaptive thinking
(per current API guidance). Outputs are short, so requests are non-streaming.

Guardrail: the AI only *suggests*. It never places orders, never bypasses the risk gate,
and authored strategies are validated against the rule DSL before they can be used.
"""

from __future__ import annotations

import json
import re

from app.analysis import indicators as ind
from app.analysis.candles import Candle, closes
from app.strategy.library import TEMPLATES
from app.strategy.rules import build_strategy

MODEL = "claude-opus-4-8"


class AIUnavailable(Exception):
    """Raised when the Anthropic SDK or API key is not configured."""


class AIClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise AIUnavailable("ANTHROPIC_API_KEY is not configured")
        self.api_key = api_key

    def _messages(self):
        try:
            import anthropic  # lazy optional import
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise AIUnavailable(
                "anthropic not installed (pip install trading-backend[ai])"
            ) from exc
        return anthropic.Anthropic(api_key=self.api_key)

    @staticmethod
    def _text(response) -> str:
        return "".join(b.text for b in response.content if b.type == "text").strip()

    # ------------------------------------------------------------- commentary
    def commentary(self, symbol: str, candles: list[Candle]) -> str:
        """A concise, plain-language read of recent price action and indicators."""
        client = self._messages()
        src = closes(candles)
        last = src[-1] if src else 0.0
        rsi = ind.rsi(src, 14)
        sma20 = ind.sma(src, 20)
        sma50 = ind.sma(src, 50)
        macd_line, signal_line, _ = ind.macd(src)
        facts = {
            "symbol": symbol,
            "last_price": round(last, 2),
            "rsi14": round(rsi[-1], 2) if rsi and rsi[-1] is not None else None,
            "sma20": round(sma20[-1], 2) if sma20 and sma20[-1] is not None else None,
            "sma50": round(sma50[-1], 2) if sma50 and sma50[-1] is not None else None,
            "macd": round(macd_line[-1], 2) if macd_line and macd_line[-1] is not None else None,
            "macd_signal": round(signal_line[-1], 2)
            if signal_line and signal_line[-1] is not None
            else None,
            "change_pct_20": round((last / src[-21] - 1) * 100, 2) if len(src) > 21 else None,
        }
        system = (
            "You are a markets analyst for a retail trading-education app. Given computed "
            "indicators for one instrument, write a concise (3-5 sentence) read of the "
            "current technical picture: trend, momentum, and notable levels. Be balanced "
            "and educational. End with one line: 'Not investment advice.' Do not give "
            "specific buy/sell instructions or price targets."
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": f"Indicators: {json.dumps(facts)}"}],
        )
        return self._text(resp)

    # --------------------------------------------------------- strategy author
    def author_strategy(self, prompt: str) -> dict:
        """Turn a natural-language description into a validated rule-DSL config."""
        client = self._messages()
        spec = (
            "Rule DSL: a JSON object with keys: name (string), indicators (object mapping "
            "a name to {kind, period, ...}), entry_long (array of {left, op, right}), "
            "exit_long (same), optional entry_short/exit_short, allow_short (bool). "
            "Indicator kinds: sma, ema, rsi, macd, macd_signal, boll_upper, boll_mid, "
            "boll_lower, vol_sma (average volume), vwap (volume-weighted avg price), atr "
            "(volatility), highest/lowest (highest high / lowest low of the previous N "
            "bars, i.e. the breakout level). An indicator spec may add 'mult' (number) to "
            "scale its line, e.g. a '2x average volume' threshold. Operands left/right are "
            "an indicator name, a number, or a source string: 'close'/'price' or 'volume'. "
            "Operators: >, >=, <, <=. Each rule list is ANDed.\n"
            "Return ONLY the JSON object, no prose.\n"
            f"Examples:\n{json.dumps(list(TEMPLATES.values())[:2], indent=2)}"
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            thinking={"type": "adaptive"},
            system=spec,
            messages=[{"role": "user", "content": prompt}],
        )
        config = _extract_json(self._text(resp))
        build_strategy(config)  # validate; raises ValueError on a bad config
        return config

    # --------------------------------------------------------------- coaching
    def coach(self, account: dict, positions: list[dict], trades_summary: dict) -> str:
        """Educational coaching on the current account state and trading behavior."""
        client = self._messages()
        system = (
            "You are a disciplined trading coach for a retail trader using a paper-trading "
            "app to learn. Given their account summary, open positions, and recent trade "
            "stats, give brief, constructive coaching focused on RISK DISCIPLINE: position "
            "sizing, risk/reward, over-trading, and cutting losses. Be encouraging but "
            "honest. 4-6 sentences. Do NOT give specific buy/sell calls or price targets. "
            "End with: 'Educational only — not investment advice.'"
        )
        payload = {"account": account, "positions": positions, "recent": trades_summary}
        resp = client.messages.create(
            model=MODEL,
            max_tokens=700,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        return self._text(resp)

    def review_trades(self, trades_summary: dict) -> str:
        """Auto-review of recent trading: patterns, strengths, and what to improve."""
        client = self._messages()
        system = (
            "You are reviewing a retail trader's recent trades for a learning journal. "
            "Identify behavioral patterns (e.g. win rate vs average win/loss, signs of "
            "over-trading or revenge trading) and give 3-5 specific, actionable lessons. "
            "Be concrete and educational. End with: 'Educational only — not investment "
            "advice.'"
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": json.dumps(trades_summary)}],
        )
        return self._text(resp)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("AI did not return valid JSON") from None
        return json.loads(match.group(0))
