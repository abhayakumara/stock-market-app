"""Trade journal: user notes plus a structured summary of recent activity for AI review.

Single-user, in-memory for now (persistence is a later step). Keeping a journal is a core
learning habit the app encourages — it pairs with the AI trade-review feature.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.backtest.metrics import trade_pnls
from app.domain.models import Trade

_ids = itertools.count(1)


@dataclass(slots=True)
class JournalEntry:
    text: str
    tags: list[str] = field(default_factory=list)
    id: int = field(default_factory=lambda: next(_ids))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


class Journal:
    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def add(self, text: str, tags: list[str] | None = None) -> JournalEntry:
        entry = JournalEntry(text=text, tags=tags or [])
        self._entries.append(entry)
        return entry

    def entries(self) -> list[JournalEntry]:
        return list(self._entries)


def summarize_trades(trades: list[Trade], limit: int = 20) -> dict:
    """A compact, model-friendly summary of recent trades and their closed P&Ls."""
    pnls = trade_pnls(trades)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    recent = trades[-limit:]
    return {
        "num_fills": len(trades),
        "closed_trades": len(pnls),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(pnls) * 100, 1) if pnls else 0.0,
        "total_pnl": round(sum(pnls), 2),
        "recent_fills": [
            {
                "symbol": t.tradingsymbol,
                "side": t.side.value,
                "qty": t.quantity,
                "price": str(t.price),
            }
            for t in recent
        ],
    }
