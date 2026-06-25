from decimal import Decimal

import pytest

from app.domain.enums import OrderType, Product, Side
from app.domain.models import Order
from app.live.controller import LiveController, LiveRejected
from app.live.risk import RiskLimits

TOKEN = 738561


def mk(side=Side.BUY, qty=10):
    return Order(
        instrument_token=TOKEN,
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
        product=Product.CNC,
    )


def armed_controller():
    c = LiveController(configured=True)
    c.acknowledge()
    c.arm()
    return c


def test_unconfigured_cannot_arm():
    c = LiveController(configured=False)
    with pytest.raises(LiveRejected):
        c.arm()


def test_must_acknowledge_before_arming():
    c = LiveController(configured=True)
    with pytest.raises(LiveRejected):
        c.arm()
    c.acknowledge()
    c.arm()
    assert c.armed


def test_authorize_blocked_when_disarmed():
    c = LiveController(configured=True)
    c.acknowledge()  # acknowledged but NOT armed
    with pytest.raises(LiveRejected) as exc:
        c.authorize(mk(), reference_price=Decimal("100"))
    assert "disarmed" in str(exc.value)


def test_authorize_passes_when_all_gates_open():
    c = armed_controller()
    c.authorize(mk(qty=10), reference_price=Decimal("100"))  # 1,000 < caps → no raise


def test_strategy_must_be_promoted():
    c = armed_controller()
    with pytest.raises(LiveRejected) as exc:
        c.authorize(mk(), reference_price=Decimal("100"), strategy_id="sma_crossover")
    assert "not promoted" in str(exc.value)
    c.promote("sma_crossover")
    c.authorize(mk(), reference_price=Decimal("100"), strategy_id="sma_crossover")


def test_risk_limits_enforced_through_controller():
    c = armed_controller()
    c.set_limits(RiskLimits(max_order_value=Decimal("500")))
    with pytest.raises(LiveRejected) as exc:
        c.authorize(mk(qty=10), reference_price=Decimal("100"))  # 1,000 > 500
    assert "per-order cap" in str(exc.value)


def test_disarm_is_always_allowed():
    c = armed_controller()
    c.disarm()
    assert not c.armed
    with pytest.raises(LiveRejected):
        c.authorize(mk(), reference_price=Decimal("100"))


def test_daily_loss_accumulates_and_halts():
    c = armed_controller()
    c.set_limits(RiskLimits(max_daily_loss=Decimal("100")))
    c.record_realized(Decimal("-150"))  # a losing trade
    with pytest.raises(LiveRejected) as exc:
        c.authorize(mk(), reference_price=Decimal("100"))
    assert "daily loss" in str(exc.value)
