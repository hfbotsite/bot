from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Engine, and_, desc, insert, select

from services.platform.db.tables import position_snapshots, positions

from .position_math import PositionState


@dataclass(slots=True)
class PositionKey:
    bot_run_id: str
    exchange: str
    symbol: str
    position_mode: str
    position_side: str


class EngineState:
    """DB-first state resolver + in-memory cache.

    Responsibilities (MVP):
    - Resolve position_id by (bot_run_id, exchange, symbol, position_mode, position_side), creating it if missing.
    - Load last known PositionState from position_snapshots (if any).
    - Cache PositionState by position_id for repeated event handling.

    Note: no writing of fills/snapshots here yet (next stages).
    """

    def __init__(self, engine: Engine):
        self._engine = engine
        self._pos_state_cache: dict[str, PositionState] = {}

    def get_or_create_position_id(self, key: PositionKey) -> str:
        with self._engine.begin() as conn:
            q = select(positions.c.id).where(
                and_(
                    positions.c.bot_run_id == key.bot_run_id,
                    positions.c.exchange == key.exchange,
                    positions.c.symbol == key.symbol,
                    positions.c.position_mode == key.position_mode,
                    positions.c.position_side == key.position_side,
                )
            )
            existing = conn.execute(q).scalar_one_or_none()
            if existing:
                return str(existing)

            # MVP: id is stored as text UUID; generation is deferred to caller in future.
            # For now we use DB-side gen via python uuid.
            import uuid

            position_id = str(uuid.uuid4())
            conn.execute(
                insert(positions).values(
                    id=position_id,
                    bot_run_id=key.bot_run_id,
                    exchange=key.exchange,
                    symbol=key.symbol,
                    position_mode=key.position_mode,
                    position_side=key.position_side,
                    status="open",
                    opened_at=datetime.utcnow(),
                )
            )
            return position_id

    def load_position_state(self, position_id: str) -> PositionState:
        if position_id in self._pos_state_cache:
            return self._pos_state_cache[position_id]

        with self._engine.begin() as conn:
            q = (
                select(
                    position_snapshots.c.qty,
                    position_snapshots.c.avg_entry_price,
                    position_snapshots.c.realized_pnl_gross,
                )
                .where(position_snapshots.c.position_id == position_id)
                .order_by(desc(position_snapshots.c.ts))
                .limit(1)
            )
            row = conn.execute(q).mappings().first()

        if not row:
            state = PositionState(qty=Decimal("0"), avg_entry_price=None, realized_pnl_gross=Decimal("0"))
        else:
            state = PositionState(
                qty=Decimal(str(row["qty"])),
                avg_entry_price=(
                    Decimal(str(row["avg_entry_price"])) if row["avg_entry_price"] is not None else None
                ),
                realized_pnl_gross=(
                    Decimal(str(row["realized_pnl_gross"])) if row["realized_pnl_gross"] is not None else Decimal("0")
                ),
            )

        self._pos_state_cache[position_id] = state
        return state

    def set_position_state(self, position_id: str, state: PositionState) -> None:
        self._pos_state_cache[position_id] = state
