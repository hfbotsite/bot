from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import text

from services.platform.db.tables import orders as orders_table

from sqlalchemy import Engine


@dataclass(frozen=True, slots=True)
class UpsertOrder:
    bot_run_id: str
    exchange: str
    symbol: str
    exchange_order_id: Optional[str]
    client_order_id: Optional[str]
    type: Optional[str]
    side: str
    position_mode: Optional[str]
    position_side: Optional[str]
    reduce_only: Optional[bool]
    price: Optional[Decimal]
    amount: Optional[Decimal]
    filled: Optional[Decimal]
    status: Optional[str]
    ts: Optional[datetime] = None


class OrdersRepo:
    def __init__(self, engine: Engine):
        self._engine = engine

    def upsert(self, o: UpsertOrder) -> None:
        # MVP upsert strategy:
        # - if client_order_id exists: use (bot_run_id, client_order_id) as natural key
        # - else if exchange_order_id exists: use (bot_run_id, exchange_order_id)
        # We don't have a DB unique constraint yet, so we do:
        # 1) try update by client_order_id
        # 2) else try update by exchange_order_id
        # 3) else insert
        # This is safe for MVP single-writer per bot-run.
        now = datetime.now(tz=timezone.utc)
        with self._engine.begin() as conn:
            if o.client_order_id:
                res = conn.execute(
                    text(
                        f"""
                        UPDATE {orders_table.name}
                        SET exchange_order_id = COALESCE(:exchange_order_id, exchange_order_id),
                            type = COALESCE(:type, type),
                            side = :side,
                            position_mode = COALESCE(:position_mode, position_mode),
                            position_side = COALESCE(:position_side, position_side),
                            reduce_only = COALESCE(:reduce_only, reduce_only),
                            price = COALESCE(:price, price),
                            amount = COALESCE(:amount, amount),
                            filled = COALESCE(:filled, filled),
                            status = COALESCE(:status, status),
                            updated_at = :updated_at
                        WHERE bot_run_id = :bot_run_id AND client_order_id = :client_order_id
                        """
                    ),
                    {
                        "bot_run_id": o.bot_run_id,
                        "client_order_id": o.client_order_id,
                        "exchange_order_id": o.exchange_order_id,
                        "type": o.type,
                        "side": o.side,
                        "position_mode": o.position_mode,
                        "position_side": o.position_side,
                        "reduce_only": o.reduce_only,
                        "price": o.price,
                        "amount": o.amount,
                        "filled": o.filled,
                        "status": o.status,
                        "updated_at": now,
                    },
                )
                if res.rowcount and res.rowcount > 0:
                    return

            if o.exchange_order_id:
                res = conn.execute(
                    text(
                        f"""
                        UPDATE {orders_table.name}
                        SET client_order_id = COALESCE(:client_order_id, client_order_id),
                            type = COALESCE(:type, type),
                            side = :side,
                            position_mode = COALESCE(:position_mode, position_mode),
                            position_side = COALESCE(:position_side, position_side),
                            reduce_only = COALESCE(:reduce_only, reduce_only),
                            price = COALESCE(:price, price),
                            amount = COALESCE(:amount, amount),
                            filled = COALESCE(:filled, filled),
                            status = COALESCE(:status, status),
                            updated_at = :updated_at
                        WHERE bot_run_id = :bot_run_id AND exchange_order_id = :exchange_order_id
                        """
                    ),
                    {
                        "bot_run_id": o.bot_run_id,
                        "exchange_order_id": o.exchange_order_id,
                        "client_order_id": o.client_order_id,
                        "type": o.type,
                        "side": o.side,
                        "position_mode": o.position_mode,
                        "position_side": o.position_side,
                        "reduce_only": o.reduce_only,
                        "price": o.price,
                        "amount": o.amount,
                        "filled": o.filled,
                        "status": o.status,
                        "updated_at": now,
                    },
                )
                if res.rowcount and res.rowcount > 0:
                    return

            # Insert new row
            import uuid

            conn.execute(
                orders_table.insert(),
                {
                    "id": str(uuid.uuid4()),
                    "bot_run_id": o.bot_run_id,
                    "exchange": o.exchange,
                    "symbol": o.symbol,
                    "exchange_order_id": o.exchange_order_id,
                    "client_order_id": o.client_order_id,
                    "type": o.type,
                    "side": o.side,
                    "position_mode": o.position_mode,
                    "position_side": o.position_side,
                    "reduce_only": o.reduce_only,
                    "price": o.price,
                    "amount": o.amount,
                    "filled": o.filled,
                    "status": o.status,
                    "created_at": now,
                    "updated_at": now,
                },
            )
