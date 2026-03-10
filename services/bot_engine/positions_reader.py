from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Engine, text


@dataclass(frozen=True, slots=True)
class PositionSnapshotView:
    position_id: str
    symbol: str
    position_mode: str
    position_side: str
    qty: Decimal
    avg_entry_price: Optional[Decimal]
    realized_pnl_gross: Optional[Decimal]
    ts: datetime


class PositionsReader:
    def __init__(self, engine: Engine):
        self._engine = engine

    def latest_snapshot(
        self,
        *,
        bot_run_id: str,
        symbol: str,
        position_mode: str,
        position_side: str,
    ) -> Optional[PositionSnapshotView]:
        # Get latest snapshot for the scoped position.
        # If no snapshots exist yet, return None.
        q = text(
            """
            SELECT
              p.id AS position_id,
              p.symbol AS symbol,
              p.position_mode AS position_mode,
              p.position_side AS position_side,
              s.qty AS qty,
              s.avg_entry_price AS avg_entry_price,
              s.realized_pnl_gross AS realized_pnl_gross,
              s.ts AS ts
            FROM positions p
            JOIN position_snapshots s ON s.position_id = p.id
            WHERE p.bot_run_id = :bot_run_id
              AND p.symbol = :symbol
              AND p.position_mode = :position_mode
              AND p.position_side = :position_side
            ORDER BY s.ts DESC
            LIMIT 1
            """
        )
        with self._engine.begin() as conn:
            row = conn.execute(
                q,
                {
                    "bot_run_id": bot_run_id,
                    "symbol": symbol,
                    "position_mode": position_mode,
                    "position_side": position_side,
                },
            ).mappings().first()

        if row is None:
            return None

        return PositionSnapshotView(
            position_id=str(row["position_id"]),
            symbol=str(row["symbol"]),
            position_mode=str(row["position_mode"]),
            position_side=str(row["position_side"]),
            qty=Decimal(str(row["qty"])),
            avg_entry_price=(Decimal(str(row["avg_entry_price"])) if row["avg_entry_price"] is not None else None),
            realized_pnl_gross=(Decimal(str(row["realized_pnl_gross"])) if row["realized_pnl_gross"] is not None else None),
            ts=row["ts"],
        )
