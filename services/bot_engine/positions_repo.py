from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Engine, update

from services.platform.db.tables import position_snapshots, positions

from .position_math import PositionState


class PositionsRepo:
    """Persistence for positions + position_snapshots (MVP).

    This stage writes:
      - positions: last known margin_mode/leverage/collateral_asset + status/opened_at/closed_at
      - position_snapshots: qty/avg_entry_price/realized_pnl_gross and margin context

    Note:
      Baseline schema stores a lot more fields in position_snapshots. MVP bot_engine
      only fills a minimal subset (others remain NULL).
    """

    def __init__(self, engine: Engine):
        self._engine = engine

    def update_position_and_insert_snapshot(
        self,
        *,
        position_id: str,
        ts: datetime,
        state: PositionState,
        margin_mode: str | None,
        leverage: Decimal | None,
        collateral_asset: str | None,
    ) -> str:
        import uuid

        snapshot_id = str(uuid.uuid4())

        with self._engine.begin() as conn:
            # Update "last known" position settings.
            conn.execute(
                update(positions)
                .where(positions.c.id == position_id)
                .values(
                    margin_mode=margin_mode,
                    leverage=leverage,
                    collateral_asset=collateral_asset,
                )
            )

            # Infer status from qty (open/closed) and set opened_at on first open.
            status = "closed" if state.qty == 0 else "open"

            if status == "open":
                # Set opened_at only if it isn't set yet (first transition to open).
                conn.execute(
                    update(positions)
                    .where(positions.c.id == position_id)
                    .where(positions.c.opened_at.is_(None))
                    .values(opened_at=ts)
                )

            conn.execute(
                update(positions)
                .where(positions.c.id == position_id)
                .values(
                    status=status,
                    closed_at=(ts if status == "closed" else None),
                )
            )

            # Sanity-check: this must exist, otherwise we are writing snapshots for a non-existent position_id.
            pos_exists = conn.execute(
                positions.select().with_only_columns(positions.c.id).where(positions.c.id == position_id)
            ).scalar_one_or_none()
            if pos_exists is None:
                raise RuntimeError(f"positions row not found for position_id={position_id}")

            conn.execute(
                position_snapshots.insert().values(
                    id=snapshot_id,
                    position_id=position_id,
                    ts=ts,
                    qty=state.qty,
                    avg_entry_price=state.avg_entry_price,
                    realized_pnl_gross=state.realized_pnl_gross,
                    margin_mode=margin_mode,
                    leverage=leverage,
                    # Baseline schema supports collateral_asset at position level, but not in snapshots.
                    # Keep it NULL for now to match schema.
                )
            )

        return snapshot_id
