"""Live order service — places REAL orders on Zerodha via Kite Connect.

This is the only component that must run on a host with a **static IP registered in the
Kite developer console** (orders from unregistered IPs are rejected since 2025-04-01).

The order interface mirrors the paper engine so a strategy/order is mode-agnostic. The
``kiteconnect`` dependency is imported lazily and the broker is only constructed once a
daily access token is available — so the rest of the app runs without it.
"""

from __future__ import annotations

from app.domain.enums import OrderType, Product, Side
from app.domain.models import Order
from app.marketdata.instruments import BY_TOKEN

# Map our enums onto Kite's order-type constants.
_KITE_ORDER_TYPE = {
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
    OrderType.SL: "SL",
    OrderType.SL_M: "SL-M",
}


class LiveUnavailable(Exception):
    """Raised when the Kite SDK/token is unavailable for live trading."""


class LiveBroker:
    def __init__(self, api_key: str, access_token: str):
        if not api_key or not access_token:
            raise LiveUnavailable("Kite API key and a daily access token are required")
        self.api_key = api_key
        self.access_token = access_token

    def _kite(self):
        try:
            from kiteconnect import KiteConnect  # lazy optional import
        except ImportError as exc:  # pragma: no cover - only without the extra
            raise LiveUnavailable(
                "kiteconnect not installed (pip install trading-backend[kite])"
            ) from exc
        kite = KiteConnect(api_key=self.api_key)
        kite.set_access_token(self.access_token)
        return kite

    def place_order(self, order: Order) -> str:
        """Place a real order and return the Kite order id."""
        inst = BY_TOKEN.get(order.instrument_token)
        if inst is None:
            raise LiveUnavailable(f"unknown instrument token {order.instrument_token}")
        kite = self._kite()
        params = {
            "variety": "regular",
            "exchange": inst.exchange,
            "tradingsymbol": inst.tradingsymbol,
            "transaction_type": "BUY" if order.side is Side.BUY else "SELL",
            "quantity": order.quantity,
            "product": order.product.value if order.product is not Product.NRML else "NRML",
            "order_type": _KITE_ORDER_TYPE[order.order_type],
        }
        if order.limit_price is not None:
            params["price"] = float(order.limit_price)
        if order.trigger_price is not None:
            params["trigger_price"] = float(order.trigger_price)
        return kite.place_order(**params)

    def positions(self) -> list[dict]:
        return self._kite().positions().get("net", [])

    def funds(self) -> dict:
        return self._kite().margins().get("equity", {})
