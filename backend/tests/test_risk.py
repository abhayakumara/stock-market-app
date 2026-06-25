from decimal import Decimal

from app.domain.enums import OrderType, Product, Side
from app.domain.models import Order
from app.live.risk import RiskLimits, RiskManager

TOKEN = 738561


def mk(side, qty):
    return Order(
        instrument_token=TOKEN,
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
        product=Product.CNC,
    )


def base_kwargs():
    return dict(
        reference_price=Decimal("100"),
        current_net_qty=0,
        current_position_value=Decimal("0"),
        open_positions=0,
        daily_loss=Decimal("0"),
    )


def test_within_limits_ok():
    rm = RiskManager(RiskLimits())
    assert rm.check(mk(Side.BUY, 50), **base_kwargs()).ok  # 5,000 < 10,000 cap


def test_order_value_cap_blocks():
    rm = RiskManager(RiskLimits(max_order_value=Decimal("1000")))
    d = rm.check(mk(Side.BUY, 50), **base_kwargs())  # 5,000 > 1,000
    assert not d.ok
    assert "per-order cap" in d.reason


def test_position_value_cap_blocks_increasing():
    rm = RiskManager(RiskLimits(max_position_value=Decimal("6000")))
    kw = base_kwargs()
    kw["current_net_qty"] = 30
    kw["current_position_value"] = Decimal("3000")
    d = rm.check(mk(Side.BUY, 40), **kw)  # 3000 + 4000 = 7000 > 6000
    assert not d.ok
    assert "per-instrument cap" in d.reason


def test_daily_loss_cap_halts_trading():
    rm = RiskManager(RiskLimits(max_daily_loss=Decimal("5000")))
    kw = base_kwargs()
    kw["daily_loss"] = Decimal("5000")
    d = rm.check(mk(Side.BUY, 1), **kw)
    assert not d.ok
    assert "daily loss" in d.reason


def test_max_open_positions_blocks_new_instrument():
    rm = RiskManager(RiskLimits(max_open_positions=2))
    kw = base_kwargs()
    kw["open_positions"] = 2  # already at max, new instrument (net 0)
    d = rm.check(mk(Side.BUY, 1), **kw)
    assert not d.ok
    assert "open positions" in d.reason


def test_reducing_position_not_capped_by_position_value():
    rm = RiskManager(RiskLimits(max_position_value=Decimal("1000")))
    kw = base_kwargs()
    kw["current_net_qty"] = 100  # long
    kw["current_position_value"] = Decimal("10000")
    # Selling reduces exposure → position-value cap does not apply.
    assert rm.check(mk(Side.SELL, 50), **kw).ok
