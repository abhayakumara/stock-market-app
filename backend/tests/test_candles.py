from datetime import UTC, datetime
from decimal import Decimal

from app.analysis.candles import CandleAggregator, SyntheticCandleProvider
from app.domain.models import Tick

TOKEN = 738561


def _tick(price, ts):
    return Tick(instrument_token=TOKEN, last_price=Decimal(str(price)), timestamp=ts, volume=10)


def test_aggregator_buckets_by_interval():
    agg = CandleAggregator(interval_seconds=60)
    base = datetime(2026, 1, 1, 9, 15, 0, tzinfo=UTC)
    agg.add(_tick(100, base))
    agg.add(_tick(105, base.replace(second=30)))  # same minute → high updates
    agg.add(_tick(95, base.replace(second=45)))  # same minute → low updates
    agg.add(_tick(102, base.replace(minute=16)))  # next minute → new candle

    candles = agg.candles(TOKEN)
    assert len(candles) == 2
    first = candles[0]
    assert first.open == 100
    assert first.high == 105
    assert first.low == 95
    assert first.close == 95
    assert first.volume == 30  # three ticks * 10


def test_synthetic_provider_is_deterministic_and_valid_ohlc():
    p = SyntheticCandleProvider()
    a = p.history(TOKEN, Decimal("2900"), count=50)
    b = p.history(TOKEN, Decimal("2900"), count=50)
    assert [c.close for c in a] == [c.close for c in b]  # deterministic per token
    assert len(a) == 50
    for c in a:
        assert c.high >= c.open >= 0
        assert c.high >= c.close
        assert c.low <= c.open
        assert c.low <= c.close
