from decimal import Decimal

import pytest

from app.domain.enums import OrderStatus, OrderType, Product, Side
from app.domain.models import Order, Tick
from app.paper.engine import InsufficientFundsError, PaperBroker

TOKEN = 256265  # NIFTY 50, arbitrary


def mk_order(side, qty, otype=OrderType.MARKET, limit=None, trigger=None, product=Product.CNC):
    return Order(
        instrument_token=TOKEN,
        side=side,
        quantity=qty,
        order_type=otype,
        product=product,
        limit_price=limit,
        trigger_price=trigger,
        tradingsymbol="TEST",
    )


def fresh(slippage="0"):
    return PaperBroker(initial_capital=Decimal("1000000"), slippage=Decimal(slippage))


def test_market_order_fills_on_next_tick():
    b = fresh()
    order = b.place_order(mk_order(Side.BUY, 10))
    assert order.status is OrderStatus.OPEN  # no price yet → rests
    trades = b.on_tick(Tick(TOKEN, Decimal("100")))
    assert len(trades) == 1
    assert order.status is OrderStatus.COMPLETE
    assert order.average_price == Decimal("100")
    assert b.get_position(TOKEN).net_quantity == 10


def test_market_slippage_applied_to_buy():
    b = fresh(slippage="0.0005")
    b.place_order(mk_order(Side.BUY, 1))
    trades = b.on_tick(Tick(TOKEN, Decimal("100")))
    assert trades[0].price == Decimal("100.05")  # 100 * (1 + 0.0005)


def test_limit_buy_rests_until_price_crosses():
    b = fresh()
    order = b.place_order(mk_order(Side.BUY, 10, OrderType.LIMIT, limit=Decimal("95")))
    assert b.on_tick(Tick(TOKEN, Decimal("100"))) == []  # above limit, no fill
    assert order.status is OrderStatus.OPEN
    trades = b.on_tick(Tick(TOKEN, Decimal("94")))  # crosses
    assert len(trades) == 1
    assert trades[0].price == Decimal("94")  # never worse than the limit
    assert order.status is OrderStatus.COMPLETE


def test_sl_m_buy_triggers_above_trigger_price():
    b = fresh()
    order = b.place_order(mk_order(Side.BUY, 10, OrderType.SL_M, trigger=Decimal("105")))
    assert b.on_tick(Tick(TOKEN, Decimal("100"))) == []  # below trigger
    assert order.triggered is False
    trades = b.on_tick(Tick(TOKEN, Decimal("106")))  # breaches
    assert len(trades) == 1
    assert order.triggered is True
    assert trades[0].price == Decimal("106")


def test_sl_m_sell_triggers_below_trigger_price():
    b = fresh()
    b.place_order(mk_order(Side.SELL, 10, OrderType.SL_M, trigger=Decimal("95")))
    assert b.on_tick(Tick(TOKEN, Decimal("96"))) == []
    trades = b.on_tick(Tick(TOKEN, Decimal("94")))
    assert len(trades) == 1
    assert trades[0].price == Decimal("94")


def test_round_trip_realizes_pnl_and_flattens_position():
    b = fresh()
    b.place_order(mk_order(Side.BUY, 10))
    b.on_tick(Tick(TOKEN, Decimal("100")))  # buy fills @100
    b.on_tick(Tick(TOKEN, Decimal("110")))  # price rises
    b.place_order(mk_order(Side.SELL, 10))  # market sell fills immediately @110
    pos = b.get_position(TOKEN)
    assert pos.net_quantity == 0
    assert pos.realized_pnl == Decimal("100")  # (110-100)*10, gross of charges
    summary = b.summary()
    # Net equity gain = gross P&L minus total charges; charges are positive.
    assert summary.equity < Decimal("1000000") + Decimal("100")
    assert summary.equity > Decimal("1000000")  # still profitable after costs


def test_position_averaging_on_pyramiding():
    b = fresh()
    b.place_order(mk_order(Side.BUY, 10))
    b.on_tick(Tick(TOKEN, Decimal("100")))  # fill @100
    b.on_tick(Tick(TOKEN, Decimal("120")))  # last → 120
    b.place_order(mk_order(Side.BUY, 10))  # immediate fill @120
    pos = b.get_position(TOKEN)
    assert pos.net_quantity == 20
    assert pos.average_price == Decimal("110")  # (100*10 + 120*10)/20


def test_insufficient_funds_rejected():
    b = PaperBroker(initial_capital=Decimal("1000"), slippage=Decimal("0"))
    b.on_tick(Tick(TOKEN, Decimal("100")))  # establish a price
    with pytest.raises(InsufficientFundsError):
        b.place_order(mk_order(Side.BUY, 100))  # needs 10,000 margin


def test_reducing_order_needs_no_new_margin():
    b = PaperBroker(initial_capital=Decimal("1000"), slippage=Decimal("0"))
    # Open a long that uses most of the cash via intraday leverage.
    b.on_tick(Tick(TOKEN, Decimal("100")))
    b.place_order(mk_order(Side.BUY, 40, product=Product.MIS))  # 4000 notional / 5x = 800
    pos = b.get_position(TOKEN)
    assert pos.net_quantity == 40
    # Selling to reduce should not be blocked by margin even with low cash.
    b.on_tick(Tick(TOKEN, Decimal("105")))
    sell = b.place_order(mk_order(Side.SELL, 40, product=Product.MIS))
    assert sell.status is OrderStatus.COMPLETE
    assert b.get_position(TOKEN).net_quantity == 0


def test_cancel_order():
    b = fresh()
    order = b.place_order(mk_order(Side.BUY, 10, OrderType.LIMIT, limit=Decimal("90")))
    b.cancel_order(order.order_id)
    assert order.status is OrderStatus.CANCELLED
    assert b.on_tick(Tick(TOKEN, Decimal("80"))) == []  # cancelled → never fills
