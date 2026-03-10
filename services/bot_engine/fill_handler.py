from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .engine_state import EngineState, PositionKey
from .events import FillEvent, PositionMode, PositionSide
from .fills_repo import FillsRepo
from .position_math import PositionState, apply_fill_wa, signed_qty
from .positions_repo import PositionsRepo
from .deals_repo import DealsRepo
from .exit_tracker import ExitIntent, ExitTracker


@dataclass(slots=True)
class FillProcessResult:
    position_id: str
    inserted: bool
    fill_id: str | None
    closed_qty_abs: Decimal
    realized_delta: Decimal
    new_state: PositionState
    snapshot_id: str | None


class FillHandler:
    """Single place to process FillEvent (MVP pipeline).

    Pipeline:
      1) resolve/create position_id (DB-first)
      2) load PositionState from cache/snapshots
      3) idempotent insert into trade_fills
      4) if inserted => apply WA math, update in-memory cache
      5) if inserted => update positions + write position_snapshots
      6) manage deal lifecycle (open on first entry fill; close when qty -> 0)

    Lot audit tables are not written in this stage.
    """

    def __init__(
        self,
        *,
        state: EngineState,
        fills_repo: FillsRepo,
        positions_repo: PositionsRepo,
        deals_repo: DealsRepo,
        exit_tracker: ExitTracker,
    ):
        self._state = state
        self._fills_repo = fills_repo
        self._positions_repo = positions_repo
        self._deals_repo = deals_repo
        self._exit_tracker = exit_tracker

    def process_fill(
        self,
        *,
        fill: FillEvent,
        position_mode: PositionMode,
        position_side: PositionSide,
    ) -> FillProcessResult:
        # 1) resolve position_id
        pos_key = PositionKey(
            bot_run_id=fill.bot_run_id,
            exchange=fill.exchange,
            symbol=fill.symbol,
            position_mode=position_mode,
            position_side=position_side,
        )
        position_id = self._state.get_or_create_position_id(pos_key)

        # 2) load state
        cur_state = self._state.load_position_state(position_id)
        prev_qty = cur_state.qty

        # 3) insert fill idempotently
        inserted, fill_id = self._fills_repo.insert_fill_idempotent(fill)

        # 4) apply only on new fill
        if not inserted:
            return FillProcessResult(
                position_id=position_id,
                inserted=False,
                fill_id=None,
                closed_qty_abs=Decimal("0"),
                realized_delta=Decimal("0"),
                new_state=cur_state,
                snapshot_id=None,
            )

        delta = signed_qty(fill.side, position_side, fill.qty)
        new_state, closed_qty_abs, realized_delta = apply_fill_wa(
            cur_state,
            position_side=position_side,
            delta_qty=delta,
            price=fill.price,
        )
        self._state.set_position_state(position_id, new_state)

        # 5) persist snapshot + last known margin context
        snapshot_id = self._positions_repo.update_position_and_insert_snapshot(
            position_id=position_id,
            ts=fill.ts,
            state=new_state,
            margin_mode=fill.margin_mode,
            leverage=fill.leverage,
            collateral_asset=fill.collateral_asset,
        )

        # 6) Exit intent inference (from fills)
        # We set exit intent when we see a reduce fill that carries an exit_reason hint.
        # This intent will be used when position finally reaches qty==0.
        if fill.exit_reason is not None and closed_qty_abs > 0:
            from datetime import datetime, timezone

            self._exit_tracker.set_exit_intent(
                intent=ExitIntent(
                    position_id=position_id,
                    bot_run_id=fill.bot_run_id,
                    symbol=fill.symbol,
                    position_side=position_side,
                    reason=fill.exit_reason,  # type: ignore[arg-type]
                    ts=datetime.now(tz=timezone.utc),
                )
            )

        # 7) Deal lifecycle
        # Open deal when first transitioning to non-zero qty.
        if prev_qty == 0 and new_state.qty != 0:
            self._deals_repo.ensure_open_deal(
                bot_run_id=fill.bot_run_id,
                position_id=position_id,
                deal_direction=position_side,
                opened_at=fill.ts,
            )

        # Close deal when transitioning to zero qty.
        if prev_qty != 0 and new_state.qty == 0:
            intent = self._exit_tracker.get_exit_intent(position_id)
            exit_reason = intent.reason if intent is not None else None
            self._deals_repo.close_deal(
                bot_run_id=fill.bot_run_id,
                position_id=position_id,
                closed_at=fill.ts,
                exit_reason=exit_reason,
            )
            self._exit_tracker.clear_exit_intent(position_id)

        return FillProcessResult(
            position_id=position_id,
            inserted=True,
            fill_id=fill_id,
            closed_qty_abs=closed_qty_abs,
            realized_delta=realized_delta,
            new_state=new_state,
            snapshot_id=snapshot_id,
        )
