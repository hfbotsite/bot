from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Engine, text

from services.platform.db.tables import deals as deals_table


@dataclass(frozen=True, slots=True)
class DealCreate:
    bot_run_id: str
    position_id: str
    deal_direction: str  # LONG/SHORT
    opened_at: datetime


class DealsRepo:
    def __init__(self, engine: Engine):
        self._engine = engine

    def ensure_open_deal(
        self,
        *,
        bot_run_id: str,
        position_id: str,
        deal_direction: str,
        opened_at: datetime,
    ) -> str:
        """Get existing open deal for (bot_run_id, position_id) or create one.

        MVP: one open deal per position.
        """
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT id
                    FROM {deals_table.name}
                    WHERE bot_run_id = :bot_run_id
                      AND position_id = :position_id
                      AND status = 'open'
                    ORDER BY opened_at DESC
                    LIMIT 1
                    """
                ),
                {"bot_run_id": bot_run_id, "position_id": position_id},
            ).scalar_one_or_none()

            if row is not None:
                return str(row)

            import uuid

            deal_id = str(uuid.uuid4())
            now = datetime.now(tz=timezone.utc)
            conn.execute(
                deals_table.insert(),
                {
                    "id": deal_id,
                    "bot_run_id": bot_run_id,
                    "position_id": position_id,
                    "deal_direction": deal_direction,
                    "status": "open",
                    "opened_at": opened_at,
                    "closed_at": None,
                    "exit_reason": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            return deal_id

    def close_deal(
        self,
        *,
        bot_run_id: str,
        position_id: str,
        closed_at: datetime,
        exit_reason: str,
    ) -> None:
        """Close currently open deal for position and set exit_reason."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE {deals_table.name}
                    SET status = 'closed',
                        closed_at = :closed_at,
                        exit_reason = :exit_reason,
                        updated_at = :updated_at
                    WHERE bot_run_id = :bot_run_id
                      AND position_id = :position_id
                      AND status = 'open'
                    """
                ),
                {
                    "bot_run_id": bot_run_id,
                    "position_id": position_id,
                    "closed_at": closed_at,
                    "exit_reason": exit_reason,
                    "updated_at": datetime.now(tz=timezone.utc),
                },
            )
