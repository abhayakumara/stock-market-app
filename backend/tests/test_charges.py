from decimal import Decimal

from app.domain.enums import Segment, Side
from app.paper.charges import ChargesModel

C = ChargesModel()


def test_delivery_buy_has_no_brokerage_but_has_stt_and_stamp():
    # Buy 100 @ 100 = 10,000 turnover, delivery.
    total = C.compute(
        price=Decimal("100"), quantity=100, side=Side.BUY, segment=Segment.EQUITY_DELIVERY
    )
    # brokerage 0; stt 0.1% = 10; stamp 0.015% = 1.50; txn 0.00297% = 0.30; sebi 0.01; gst on (0+0.30+0.01)=0.06
    assert total == Decimal("10") + Decimal("1.50") + Decimal("0.30") + Decimal("0.01") + Decimal("0.06")


def test_intraday_buy_has_capped_brokerage_and_no_stt():
    # Large turnover so brokerage hits the ₹20 cap; intraday buy → no STT.
    total = C.compute(
        price=Decimal("1000"), quantity=1000, side=Side.BUY, segment=Segment.EQUITY_INTRADAY
    )
    # turnover 10,00,000. brokerage min(0.03%*1e6=300, 20)=20. stt(buy intraday)=0.
    # txn 0.00297%*1e6 = 29.70; sebi 1.00; gst on (20+29.70+1.00)=50.70*0.18=9.126->9.13
    # stamp intraday buy 0.003%*1e6 = 30.
    assert total == Decimal("20") + Decimal("29.70") + Decimal("1.00") + Decimal("9.13") + Decimal("30")


def test_intraday_sell_has_stt_but_no_stamp():
    total_sell = C.compute(
        price=Decimal("1000"), quantity=1000, side=Side.SELL, segment=Segment.EQUITY_INTRADAY
    )
    # stt sell intraday 0.025%*1e6 = 250; stamp 0 (sell). brokerage 20; txn 29.70; sebi 1; gst 9.13
    assert total_sell == Decimal("250") + Decimal("20") + Decimal("29.70") + Decimal("1.00") + Decimal("9.13")


def test_charges_scale_and_are_positive():
    small = C.compute(price=Decimal("50"), quantity=1, side=Side.BUY, segment=Segment.EQUITY_DELIVERY)
    big = C.compute(price=Decimal("50"), quantity=1000, side=Side.BUY, segment=Segment.EQUITY_DELIVERY)
    assert small > 0
    assert big > small
