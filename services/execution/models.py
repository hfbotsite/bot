from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Mapping, Optional


ExchangeId = Literal[
    "binance",
    "bybit",
    "bingx",
    "kucoinfutures",
    "mexc",
    "gateio",
    "okx",
    "htx",
]

OrderStatus = Literal[
    "created",
    "open",
    "partially_filled",
    "filled",
    "canceled",
    "rejected",
]

OrderType = Literal[
    "market",
    "limit",
    "stop",
    "stop_limit",
    "take_profit",
    "take_profit_limit",
    "unknown",
]

OrderSide = Literal["buy", "sell"]
PositionMode = Literal["one_way", "hedge"]
PositionSide = Literal["ONE_WAY", "LONG", "SHORT"]
MarginMode = Literal["cross", "isolated"]


@dataclass(frozen=True, slots=True)
class NormalizedOrderRequest:
    exchange: ExchangeId
    symbol: str

    type: OrderType
    side: OrderSide

    # Required for hedge-mode futures; for one-way can be None or "ONE_WAY"
    position_mode: PositionMode
    position_side: Optional[PositionSide]

    amount: Decimal
    price: Optional[Decimal] = None

    reduce_only: bool = False
    client_order_id: Optional[str] = None

    extra: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class NormalizedOrder:
    exchange: ExchangeId
    symbol: str

    exchange_order_id: Optional[str]
    client_order_id: Optional[str]

    status: OrderStatus
    type: OrderType
    side: OrderSide

    position_mode: Optional[PositionMode]
    position_side: Optional[PositionSide]
    reduce_only: Optional[bool]

    price: Optional[Decimal]
    amount: Optional[Decimal]
    filled: Optional[Decimal]
    avg_price: Optional[Decimal]

    ts: Optional[datetime]

    raw: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class NormalizedFill:
    # Unique ID for de-duplication (could be exchange_trade_id or hash).
    event_id: str

    ts: datetime

    exchange: ExchangeId
    symbol: str

    exchange_trade_id: str
    exchange_order_id: Optional[str]
    client_order_id: Optional[str]

    side: OrderSide
    position_side: Optional[PositionSide]

    price: Decimal
    qty: Decimal
    quote_qty: Optional[Decimal]

    fee_cost: Optional[Decimal]
    fee_currency: Optional[str]
    is_maker: Optional[bool]

    margin_mode: Optional[MarginMode]
    leverage: Optional[Decimal]
    collateral_asset: Optional[str]

    raw: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class NormalizedPosition:
    exchange: ExchangeId
    symbol: str

    position_mode: PositionMode
    position_side: PositionSide

    qty: Decimal
    avg_entry_price: Optional[Decimal]

    mark_price: Optional[Decimal]
    liquidation_price: Optional[Decimal]

    unrealized_pnl: Optional[Decimal]
    leverage: Optional[Decimal]
    margin_mode: Optional[MarginMode]
    collateral_asset: Optional[str]

    raw: Mapping[str, Any] | None = None


def validate_order_request(req: NormalizedOrderRequest) -> None:
    if req.position_mode == "hedge":
        if req.position_side not in ("LONG", "SHORT"):
            raise ValueError("hedge mode requires position_side LONG|SHORT")
    else:
        # one_way
        if req.position_side not in (None, "ONE_WAY"):
            raise ValueError("one_way mode does not allow position_side LONG|SHORT")
