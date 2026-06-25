"""Pydantic request/response models for the API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import OrderType, Product, Side


class InstrumentOut(BaseModel):
    instrument_token: int
    tradingsymbol: str
    name: str
    exchange: str
    last_price: Decimal | None = None


class PlaceOrderIn(BaseModel):
    instrument_token: int
    side: Side
    quantity: int = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    product: Product = Product.MIS
    limit_price: Decimal | None = None
    trigger_price: Decimal | None = None


class OrderOut(BaseModel):
    order_id: str
    instrument_token: int
    tradingsymbol: str
    side: Side
    quantity: int
    filled_quantity: int
    order_type: OrderType
    product: Product
    status: str
    average_price: Decimal | None
    limit_price: Decimal | None
    trigger_price: Decimal | None
    reject_reason: str = ""


class PositionOut(BaseModel):
    instrument_token: int
    tradingsymbol: str
    net_quantity: int
    average_price: Decimal
    last_price: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_charges: Decimal


class AccountOut(BaseModel):
    cash: Decimal
    equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_charges: Decimal
