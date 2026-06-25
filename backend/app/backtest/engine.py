"""The backtest replay loop.

For each candle we (1) push the close as a tick into the broker — updating marks and
filling any working orders — then (2) ask the strategy for its target signal and (3)
issue market orders to move the position to that target. Crucially the broker and charges
model are identical to live paper trading, giving backtest↔paper parity.

To keep closed-trade accounting clean, direction flips always pass through flat: we close
to zero first, then open the new side (two orders in the same bar).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.analysis.candles import Candle
from app.domain.enums import OrderType, Product, Side
from app.domain.models import Order, Tick
from app.paper.charges import ChargesModel
from app.paper.engine import InsufficientFundsError, PaperBroker
from app.strategy.base import Signal, Strategy

from .metrics import ReportCard, build_report


@dataclass(slots=True)
class BacktestResult:
    report: ReportCard
    equity_curve: list[dict]  # [{"timestamp", "equity"}]
    trades: list[dict]
    warmup: int

    def as_dict(self) -> dict:
        return {
            "report": self.report.as_dict(),
            "equity_curve": self.equity_curve,
            "trades": self.trades,
            "warmup": self.warmup,
        }


@dataclass(slots=True)
class _Settings:
    initial_capital: Decimal = Decimal("1000000")
    quantity: int = 1
    product: Product = Product.MIS
    slippage: Decimal = Decimal("0.0005")
    warmup: int = 50  # bars to seed indicators before trading begins
    charges: ChargesModel = field(default_factory=ChargesModel)


def _target_qty(signal: Signal, quantity: int) -> int:
    if signal is Signal.LONG:
        return quantity
    if signal is Signal.SHORT:
        return -quantity
    return 0


def _place(broker: PaperBroker, token: int, side: Side, qty: int, product: Product) -> None:
    try:
        broker.place_order(
            Order(
                instrument_token=token,
                side=side,
                quantity=qty,
                order_type=OrderType.MARKET,
                product=product,
            )
        )
    except InsufficientFundsError:
        # Skip trades that can't be funded; the equity curve reflects the missed move.
        pass


def run_backtest(
    *,
    candles: list[Candle],
    strategy: Strategy,
    instrument_token: int,
    initial_capital: Decimal = Decimal("1000000"),
    quantity: int = 1,
    product: Product = Product.MIS,
    slippage: Decimal = Decimal("0.0005"),
    warmup: int = 50,
) -> BacktestResult:
    cfg = _Settings(
        initial_capital=initial_capital,
        quantity=quantity,
        product=product,
        slippage=slippage,
        warmup=warmup,
    )
    broker = PaperBroker(
        initial_capital=cfg.initial_capital, charges=cfg.charges, slippage=cfg.slippage
    )

    equity_curve: list[dict] = []
    equity_values: list[float] = []

    for i, candle in enumerate(candles):
        # 1) mark the bar (fills any working orders; updates unrealized P&L)
        broker.on_tick(
            Tick(instrument_token, Decimal(str(candle.close)), timestamp=candle.timestamp)
        )

        # 2) decide and (3) act, only after warmup
        if i >= cfg.warmup:
            pos = broker.get_position(instrument_token)
            current = pos.net_quantity if pos else 0
            target = _target_qty(strategy.signal(candles[: i + 1], current), cfg.quantity)
            if target != current:
                # flip through flat for clean trade accounting
                if current != 0 and (current > 0) != (target > 0) and target != 0:
                    _place(broker, instrument_token, Side.SELL if current > 0 else Side.BUY,
                           abs(current), cfg.product)
                    _place(broker, instrument_token, Side.BUY if target > 0 else Side.SELL,
                           abs(target), cfg.product)
                else:
                    delta = target - current
                    _place(broker, instrument_token, Side.BUY if delta > 0 else Side.SELL,
                           abs(delta), cfg.product)

        eq = float(broker.summary().equity)
        equity_values.append(eq)
        equity_curve.append({"timestamp": candle.timestamp.isoformat(), "equity": round(eq, 2)})

    report = build_report(
        initial_capital=float(cfg.initial_capital),
        equity_curve=equity_values,
        trades=broker.trades,
        total_charges=float(broker.summary().total_charges),
    )
    trades_out = [
        {
            "timestamp": t.timestamp.isoformat(),
            "side": t.side.value,
            "quantity": t.quantity,
            "price": str(t.price),
            "charges": str(t.charges),
        }
        for t in broker.trades
    ]
    return BacktestResult(
        report=report, equity_curve=equity_curve, trades=trades_out, warmup=cfg.warmup
    )
