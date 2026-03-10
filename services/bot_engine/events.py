from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional


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

Side = Literal["buy", "sell"]
PositionMode = Literal["one_way", "hedge"]
PositionSide = Literal["ONE_WAY", "LONG", "SHORT"]
MarginMode = Literal["cross", "isolated"]


@dataclass(frozen=True, slots=True)
class OrderEvent:
    event_id: str
    ts: datetime
    bot_run_id: str

    exchange: str
    symbol: str

    exchange_order_id: Optional[str]
    client_order_id: Optional[str]

    status: OrderStatus
    type: OrderType
    side: Side

    position_mode: Optional[PositionMode]
    position_side: Optional[PositionSide]
    reduce_only: Optional[bool]

    price: Optional[Decimal]
    amount: Optional[Decimal]
    filled: Optional[Decimal]


@dataclass(frozen=True, slots=True)
class FillEvent:
    # Unique ID for engine event de-duplication.
    event_id: str

    # Exchange execution timestamp.
    ts: datetime

    bot_run_id: str

    exchange: str
    symbol: str

    # Unique trade id provided by exchange (ccxt: trade['id']).
    exchange_trade_id: str

    # Optional linkage to our orders table.
    order_id: Optional[str]

    side: Side

    # Required for hedge-mode futures; for one-way can be "ONE_WAY".
    position_side: Optional[PositionSide]

    price: Decimal
    qty: Decimal
    quote_qty: Optional[Decimal]

    fee_cost: Optional[Decimal]
    fee_currency: Optional[str]
    is_maker: Optional[bool]

    # Margin context (nullable; exchange may not provide it per-fill)
    margin_mode: Optional[MarginMode]
    leverage: Optional[Decimal]
    collateral_asset: Optional[str]

    # Optional exchange order ids for attribution / exit reason inference.
    exchange_order_id: Optional[str] = None
    client_order_id: Optional[str] = None

    # Optional exit reason hint (filled from execution intent registry when possible).
    exit_reason: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PositionMarkEvent:
    event_id: str
    ts: datetime
    bot_run_id: str

    exchange: str
    symbol: str
    position_side: PositionSide

    mark_price: Decimal
