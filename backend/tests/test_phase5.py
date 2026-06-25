from decimal import Decimal

from app.alerts import Alert, AlertBook
from app.domain.enums import Side
from app.domain.models import Tick, Trade
from app.journal import Journal, summarize_trades
from app.observability import Metrics

TOKEN = 738561


def test_alert_fires_once_when_price_crosses_above():
    book = AlertBook()
    book.add(Alert(instrument_token=TOKEN, op=">", price=Decimal("100"), tradingsymbol="X"))
    assert book.evaluate(Tick(TOKEN, Decimal("99"))) == []  # below threshold
    fired = book.evaluate(Tick(TOKEN, Decimal("101")))  # crosses
    assert len(fired) == 1
    assert fired[0].triggered_price == Decimal("101")
    # One-shot: does not fire again.
    assert book.evaluate(Tick(TOKEN, Decimal("102"))) == []


def test_alert_below_and_remove():
    book = AlertBook()
    a = book.add(Alert(instrument_token=TOKEN, op="<", price=Decimal("50")))
    assert book.evaluate(Tick(TOKEN, Decimal("49")))[0].id == a.id
    assert book.remove(a.id) is True
    assert book.list() == []


def test_alert_ignores_other_instruments():
    book = AlertBook()
    book.add(Alert(instrument_token=TOKEN, op=">", price=Decimal("100")))
    assert book.evaluate(Tick(999, Decimal("200"))) == []


def test_journal_add_and_list():
    j = Journal()
    j.add("Took a breakout trade, exited too early.", tags=["psychology"])
    entries = j.entries()
    assert len(entries) == 1
    assert "breakout" in entries[0].text
    assert entries[0].tags == ["psychology"]


def test_summarize_trades_round_trip():
    trades = [
        Trade("1", TOKEN, Side.BUY, 10, Decimal("100"), Decimal("0"), tradingsymbol="X"),
        Trade("2", TOKEN, Side.SELL, 10, Decimal("110"), Decimal("0"), tradingsymbol="X"),
    ]
    summary = summarize_trades(trades)
    assert summary["closed_trades"] == 1
    assert summary["wins"] == 1
    assert summary["total_pnl"] == 100.0


def test_metrics_counters():
    m = Metrics()
    m.inc("ticks")
    m.inc("ticks", 4)
    snap = m.snapshot()
    assert snap["counters"]["ticks"] == 5
    assert "uptime_seconds" in snap
