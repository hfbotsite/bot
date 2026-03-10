from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import Engine, and_, desc, insert, select, update

from services.platform.db.tables import position_snapshots, positions



@dataclass(frozen=True, slots=True)
class BootstrapPosition:
    exchange: str
    symbol: str
    position_mode: str  # one_way/hedge
    position_side: str  # LONG/SHORT/ONE_WAY
    qty: Decimal
    avg_entry_price: Decimal | None
    mark_price: Decimal | None
    unrealized_pnl_gross: Decimal | None
    realized_pnl_gross: Decimal | None
    leverage: Decimal | None
    initial_margin: Decimal | None
    liquidation_price: Decimal | None
    margin_mode: str | None
    collateral_asset: str | None
    ts: datetime


def _d(x: Any) -> Decimal | None:
    if x is None:
        return None
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def map_ccxt_position_to_bootstrap(*, p: dict[str, Any], exchange: str, position_mode: str) -> BootstrapPosition:
    # CCXT: side 'long'/'short', contracts is position size
    side = (p.get("side") or "").lower()
    position_side = "LONG" if side == "long" else "SHORT" if side == "short" else "ONE_WAY"

    ts = _now()
    # prefer CCXT timestamps if present
    if p.get("lastUpdateTimestamp"):
        ts = datetime.fromtimestamp(int(p["lastUpdateTimestamp"]) / 1000, tz=timezone.utc)

    return BootstrapPosition(
        exchange=exchange,
        symbol=str(p.get("symbol")),
        position_mode=position_mode,
        position_side=position_side,
        qty=_d(p.get("contracts")) or Decimal("0"),
        avg_entry_price=_d(p.get("entryPrice")),
        mark_price=_d(p.get("markPrice")),
        unrealized_pnl_gross=_d(p.get("unrealizedPnl")),
        realized_pnl_gross=_d(p.get("realizedPnl")),
        leverage=_d(p.get("leverage")),
        initial_margin=_d(p.get("initialMargin")),
        liquidation_price=_d(p.get("liquidationPrice")),
        margin_mode=p.get("marginMode"),
        collateral_asset=None,  # CCXT normalized position doesn't expose settle currency consistently
        ts=ts,
    )


class BootstrapSync:
    """Bootstrap current exchange positions into DB snapshots/state.

    Why:
      EngineState computes PositionState from our own position_snapshots.
      If bot starts while a position already exists on exchange (manual trade / crash / previous run),
      then our DB has positions row but qty=0 (no snapshots). This makes the bot "blind" to real exposure.

    What it does:
      - Ensure positions row exists for each non-zero position
      - Update last known leverage/margin_mode/collateral_asset in positions
      - Insert an initial position_snapshots row with qty/avg_entry_price + mark/unrealized etc.
    """

    def __init__(self, engine: Engine):
        self._engine = engine

    def sync_positions(
        self,
        *,
        bot_run_id: str,
        positions_in: Iterable[BootstrapPosition],
    ) -> int:
        inserts = 0
        with self._engine.begin() as conn:
            for bp in positions_in:
                if bp.qty == 0:
                    continue

                # 1) resolve/create position id
                q = select(positions.c.id).where(
                    and_(
                        positions.c.bot_run_id == bot_run_id,
                        positions.c.exchange == bp.exchange,
                        positions.c.symbol == bp.symbol,
                        positions.c.position_mode == bp.position_mode,
                        positions.c.position_side == bp.position_side,
                    )
                )
                position_id = conn.execute(q).scalar_one_or_none()

                if position_id is None:
                    import uuid

                    position_id = str(uuid.uuid4())
                    conn.execute(
                        insert(positions).values(
                            id=position_id,
                            bot_run_id=bot_run_id,
                            exchange=bp.exchange,
                            symbol=bp.symbol,
                            position_mode=bp.position_mode,
                            position_side=bp.position_side,
                            status="open",
                            opened_at=bp.ts,
                            margin_mode=bp.margin_mode,
                            leverage=bp.leverage,
                            collateral_asset=bp.collateral_asset,
                        )
                    )
                else:
                    position_id = str(position_id)
                    conn.execute(
                        update(positions)
                        .where(positions.c.id == position_id)
                        .values(
                            status="open",
                            margin_mode=bp.margin_mode,
                            leverage=bp.leverage,
                            collateral_asset=bp.collateral_asset,
                            closed_at=None,
                        )
                    )

                # 2) idempotent-ish snapshot insert:
                # Do not append a snapshot if the last snapshot already matches qty+avg_entry_price.
                last_q = (
                    select(position_snapshots.c.qty, position_snapshots.c.avg_entry_price)
                    .where(position_snapshots.c.position_id == position_id)
                    .order_by(desc(position_snapshots.c.ts))
                    .limit(1)
                )
                last = conn.execute(last_q).mappings().first()
                if last is not None:
                    last_qty = Decimal(str(last["qty"]))
                    last_avg = last["avg_entry_price"]
                    last_avg_d = Decimal(str(last_avg)) if last_avg is not None else None

                    if last_qty == bp.qty and last_avg_d == bp.avg_entry_price:
                        continue

                import uuid

                snapshot_id = str(uuid.uuid4())
                conn.execute(
                    insert(position_snapshots).values(
                        id=snapshot_id,
                        position_id=position_id,
                        ts=bp.ts,
                        qty=bp.qty,
                        avg_entry_price=bp.avg_entry_price,
                        mark_price=bp.mark_price,
                        unrealized_pnl_gross=bp.unrealized_pnl_gross,
                        realized_pnl_gross=bp.realized_pnl_gross,
                        leverage=bp.leverage,
                        initial_margin=bp.initial_margin,
                        liquidation_price=bp.liquidation_price,
                        margin_mode=bp.margin_mode,
                    )
                )
                inserts += 1

        return inserts
