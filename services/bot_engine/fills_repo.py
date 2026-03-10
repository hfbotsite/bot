from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Engine, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.platform.db.tables import trade_fills

from .events import FillEvent


class FillsRepo:
    """Persistence for trade_fills (MVP).

    Idempotency is ensured via unique constraint:
      uq_trade_fills_exchange_symbol_trade_id (exchange, symbol, exchange_trade_id)

    Note:
      Our NormalizedFill.event_id is currently derived from exchange + exchange_trade_id.
      Baseline schema doesn't store event_id explicitly, so this unique constraint is sufficient.
    """

    def __init__(self, engine: Engine):
        self._engine = engine

    def insert_fill_idempotent(self, fill: FillEvent) -> tuple[bool, Optional[str]]:
        """Insert fill into trade_fills if not exists.

        Returns:
          (inserted, fill_id)
        fill_id may be None if not inserted and lookup is not performed.
        """

        # Generate our internal UUID for trade_fills.id
        import uuid

        fill_id = str(uuid.uuid4())

        values = dict(
            id=fill_id,
            bot_run_id=fill.bot_run_id,
            order_id=fill.order_id,
            exchange=fill.exchange,
            symbol=fill.symbol,
            exchange_trade_id=fill.exchange_trade_id,
            ts=fill.ts,
            side=fill.side,
            position_side=fill.position_side,
            margin_mode=fill.margin_mode,
            leverage=fill.leverage,
            collateral_asset=fill.collateral_asset,
            price=fill.price,
            qty=fill.qty,
            quote_qty=fill.quote_qty,
            fee_cost=fill.fee_cost,
            fee_currency=fill.fee_currency,
            is_maker=fill.is_maker,
        )

        stmt = pg_insert(trade_fills).values(**values)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_trade_fills_exchange_symbol_trade_id").returning(
            trade_fills.c.id
        )

        # NOTE:
        # Some driver/SQLAlchemy combos may not provide reliable rowcount for INSERT .. ON CONFLICT DO NOTHING.
        # We use RETURNING to detect actual insertion.
        with self._engine.begin() as conn:
            row = conn.execute(stmt).scalar_one_or_none()
            if row is None:
                return False, None
            return True, str(row)
