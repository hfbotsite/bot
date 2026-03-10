from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from services.bot_runtime.price_feed import PriceFeed
from services.bot_runtime.signal_store import SignalStore
from services.execution.models import NormalizedOrderRequest, PositionSide

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _ensure_pos(x: Decimal, name: str) -> None:
    if x <= 0:
        raise ValueError(f"{name} must be > 0")


@dataclass(frozen=True, slots=True)
class AveragingConfig:
    """Config for dynamic averaging.

    Notes:
      - range_cover_pct is expressed in percent units (4 means 4%)
      - poll_s controls monitor loop frequency (must be small but not too small)
    """

    range_cover_pct: Decimal = Decimal("4")
    first_so_coeff: Decimal = Decimal("1.1")
    dynamic_so_coeff: Decimal = Decimal("1.8")
    new_order_time_s: int = 120
    poll_s: float = 0.5

    def validate(self) -> None:
        _ensure_pos(self.range_cover_pct, "range_cover_pct")
        _ensure_pos(self.first_so_coeff, "first_so_coeff")
        _ensure_pos(self.dynamic_so_coeff, "dynamic_so_coeff")
        if self.new_order_time_s < 0:
            raise ValueError("new_order_time_s must be >= 0")
        if self.poll_s <= 0:
            raise ValueError("poll_s must be > 0")


class DynamicAveragingGrid:
    """Legacy-compatible dynamic averaging grid (virtual).

    Formula (percent in config):
      First averaging:
        LONG: entry - entry * (first_so_coeff * range_cover / 100)
        SHORT: entry + entry * (first_so_coeff * range_cover / 100)

      Subsequent (so_index >= 1, where so_index is 1 for the *first* SO):
        LONG: last - last * (range_cover * dynamic_so_coeff**so_index) / 100
        SHORT: last + last * (range_cover * dynamic_so_coeff**so_index) / 100
    """

    def __init__(self, *, cfg: AveragingConfig):
        cfg.validate()
        self._cfg = cfg

    def next_level_price(
        self,
        *,
        position_side: PositionSide,
        entry_price: Decimal,
        so_index: int,
        last_anchor_price: Decimal | None,
    ) -> Decimal:
        if entry_price <= 0:
            raise ValueError("entry_price must be > 0")
        if so_index < 0:
            raise ValueError("so_index must be >= 0")

        rc = self._cfg.range_cover_pct
        if so_index == 0:
            step_pct = self._cfg.first_so_coeff * rc
            base = entry_price
        else:
            if last_anchor_price is None:
                raise ValueError("last_anchor_price required when so_index > 0")
            step_pct = rc * (self._cfg.dynamic_so_coeff ** Decimal(so_index))
            base = last_anchor_price

        delta = base * (step_pct / Decimal("100"))
        if position_side == "LONG":
            return base - delta
        if position_side == "SHORT":
            return base + delta
        raise ValueError("position_side must be LONG|SHORT")

    def in_averaging_zone(
        self,
        *,
        position_side: PositionSide,
        mark_price: Decimal,
        level_price: Decimal,
    ) -> bool:
        if position_side == "LONG":
            return mark_price <= level_price
        if position_side == "SHORT":
            return mark_price >= level_price
        raise ValueError("position_side must be LONG|SHORT")

    def should_stop_monitor(
        self,
        *,
        position_side: PositionSide,
        mark_price: Decimal,
        level_price: Decimal,
    ) -> bool:
        # Stop immediately when price leaves the zone (mirror logic).
        if position_side == "LONG":
            return mark_price > level_price
        if position_side == "SHORT":
            return mark_price < level_price
        raise ValueError("position_side must be LONG|SHORT")


@dataclass(slots=True)
class AveragingState:
    so_index: int = 0
    last_anchor_price: Decimal | None = None
    cooldown_until: datetime = field(default_factory=lambda: datetime.min.replace(tzinfo=timezone.utc))
    monitor_task: asyncio.Task[None] | None = None
    monitor_id: int = 0
    last_order_fingerprint: str | None = None
    last_order_ts: datetime | None = None


@dataclass(frozen=True, slots=True)
class AveragingSnapshot:
    """Optional snapshot for debugging/telemetry (not persisted)."""

    so_index: int
    last_anchor_price: Decimal | None
    cooldown_until: datetime
    monitor_running: bool


class AveragingCoordinator:
    """Coordinates dynamic averaging monitors and produces market averaging orders.

    Key properties:
      - Non-blocking: monitor runs in separate tasks.
      - Safe: single monitor per (symbol, position_side) guarded by lock + monitor_id.
      - Idempotent: dedup by cooldown and order fingerprint.

    Integration pattern:
      - Call tick(...) from strategy loop.
      - Call consume_orders(...) and append to strategy decision desired_orders.
      - Call reset_if_flat(...) each tick to clear state when position is closed.
    """

    def __init__(
        self,
        *,
        bot_id: str,
        exchange: str,
        position_mode: str,
        cfg: AveragingConfig,
        price_feed: PriceFeed,
        signals: SignalStore,
        amount_resolver: Callable[
            [str, PositionSide, int, Decimal, Decimal],
            Decimal,
        ],
    ):
        self._bot_id = bot_id
        self._exchange = exchange
        self._position_mode = position_mode
        self._cfg = cfg
        self._grid = DynamicAveragingGrid(cfg=cfg)
        self._price_feed = price_feed
        self._signals = signals
        self._amount_resolver = amount_resolver

        self._states: dict[tuple[str, PositionSide], AveragingState] = {}
        self._locks: dict[tuple[str, PositionSide], asyncio.Lock] = {}
        self._pending_orders: dict[tuple[str, PositionSide], list[NormalizedOrderRequest]] = {}

    def _key(self, *, symbol: str, position_side: PositionSide) -> tuple[str, PositionSide]:
        return (symbol, position_side)

    def _lock_for(self, key: tuple[str, PositionSide]) -> asyncio.Lock:
        lk = self._locks.get(key)
        if lk is None:
            lk = asyncio.Lock()
            self._locks[key] = lk
        return lk

    def _state_for(self, key: tuple[str, PositionSide]) -> AveragingState:
        st = self._states.get(key)
        if st is None:
            st = AveragingState()
            self._states[key] = st
        return st

    def snapshot(self, *, symbol: str, position_side: PositionSide) -> AveragingSnapshot:
        key = self._key(symbol=symbol, position_side=position_side)
        st = self._state_for(key)
        return AveragingSnapshot(
            so_index=st.so_index,
            last_anchor_price=st.last_anchor_price,
            cooldown_until=st.cooldown_until,
            monitor_running=(st.monitor_task is not None and not st.monitor_task.done()),
        )

    def consume_orders(self, *, symbol: str, position_side: PositionSide) -> list[NormalizedOrderRequest]:
        key = self._key(symbol=symbol, position_side=position_side)
        out = self._pending_orders.pop(key, [])
        return out

    def _enqueue(self, key: tuple[str, PositionSide], req: NormalizedOrderRequest) -> None:
        self._pending_orders.setdefault(key, []).append(req)

    async def reset_if_flat(
        self,
        *,
        symbol: str,
        position_side: PositionSide,
        position_qty: Decimal,
        avg_entry_price: Decimal | None,
    ) -> None:
        if position_qty != 0 and avg_entry_price is not None:
            return

        key = self._key(symbol=symbol, position_side=position_side)
        async with self._lock_for(key):
            st = self._state_for(key)
            st.so_index = 0
            st.last_anchor_price = None
            st.cooldown_until = datetime.min.replace(tzinfo=timezone.utc)
            st.last_order_fingerprint = None
            st.last_order_ts = None
            await self._stop_monitor_locked(key, st)

    async def tick(
        self,
        *,
        symbol: str,
        position_side: PositionSide,
        position_qty: Decimal,
        avg_entry_price: Decimal | None,
    ) -> None:
        """Fast coordinator tick; safe to call each strategy loop iteration."""
        if position_qty == 0 or avg_entry_price is None:
            await self.reset_if_flat(
                symbol=symbol,
                position_side=position_side,
                position_qty=position_qty,
                avg_entry_price=avg_entry_price,
            )
            return

        tick = self._price_feed.latest_price(symbol=symbol)
        if tick is None:
            return

        # Prefer MarkPrice if present; fallback to tick.price.
        mark_price = getattr(tick, "mark_price", None)
        if mark_price is None:
            mark_price = tick.price

        key = self._key(symbol=symbol, position_side=position_side)
        async with self._lock_for(key):
            st = self._state_for(key)

            level = self._grid.next_level_price(
                position_side=position_side,
                entry_price=avg_entry_price,
                so_index=st.so_index,
                last_anchor_price=st.last_anchor_price,
            )

            in_zone = self._grid.in_averaging_zone(position_side=position_side, mark_price=mark_price, level_price=level)
            if in_zone:
                await self._ensure_monitor_locked(
                    key,
                    st,
                    symbol=symbol,
                    position_side=position_side,
                    entry_price=avg_entry_price,
                )
            else:
                await self._stop_monitor_locked(key, st)

    async def _ensure_monitor_locked(
        self,
        key: tuple[str, PositionSide],
        st: AveragingState,
        *,
        symbol: str,
        position_side: PositionSide,
        entry_price: Decimal,
    ) -> None:
        # Single-monitor guarantee
        if st.monitor_task is not None and not st.monitor_task.done():
            return

        st.monitor_id += 1
        mid = st.monitor_id
        st.monitor_task = asyncio.create_task(
            self._monitor_loop(
                key=key,
                monitor_id=mid,
                symbol=symbol,
                position_side=position_side,
                entry_price=entry_price,
            ),
            name=f"avg_monitor:{symbol}:{position_side}:{mid}",
        )

    async def _stop_monitor_locked(self, key: tuple[str, PositionSide], st: AveragingState) -> None:
        if st.monitor_task is None:
            return
        if st.monitor_task.done():
            st.monitor_task = None
            return

        st.monitor_id += 1  # invalidate loop
        st.monitor_task.cancel()
        try:
            await st.monitor_task
        except Exception:
            pass
        finally:
            st.monitor_task = None

    async def _monitor_loop(
        self,
        *,
        key: tuple[str, PositionSide],
        monitor_id: int,
        symbol: str,
        position_side: PositionSide,
        entry_price: Decimal,
    ) -> None:
        try:
            while True:
                await asyncio.sleep(self._cfg.poll_s)

                tick = self._price_feed.latest_price(symbol=symbol)
                if tick is None:
                    continue

                mark_price = getattr(tick, "mark_price", None)
                if mark_price is None:
                    mark_price = tick.price

                async with self._lock_for(key):
                    st = self._state_for(key)
                    if st.monitor_id != monitor_id:
                        return

                    level = self._grid.next_level_price(
                        position_side=position_side,
                        entry_price=entry_price,
                        so_index=st.so_index,
                        last_anchor_price=st.last_anchor_price,
                    )

                    # Exit condition: price left zone
                    if self._grid.should_stop_monitor(
                        position_side=position_side,
                        mark_price=mark_price,
                        level_price=level,
                    ):
                        return

                    # Signal gating
                    sig = self._signals.get(symbol=symbol, event="averaging")
                    if sig is None or sig.side == "none":
                        continue
                    if position_side == "LONG" and sig.side != "long":
                        continue
                    if position_side == "SHORT" and sig.side != "short":
                        continue

                    # Cooldown
                    now = _utcnow()
                    if now < st.cooldown_until:
                        continue

                    amount = self._amount_resolver(symbol, position_side, st.so_index, entry_price, mark_price)
                    if amount <= 0:
                        logger.warning(
                            "Averaging amount resolver returned non-positive amount; skipping",
                            extra={"symbol": symbol, "position_side": position_side, "amount": str(amount)},
                        )
                        continue

                    side = "buy" if position_side == "LONG" else "sell"

                    # fingerprint uses current so_index (before increment)
                    fp = f"{self._bot_id}:{symbol}:{position_side}:so{st.so_index}:mkt"
                    if st.last_order_fingerprint == fp and st.last_order_ts is not None:
                        if (now - st.last_order_ts).total_seconds() < 2.0:
                            continue

                    # Apply cooldown and advance state immediately (per requirement: created == occurred)
                    st.cooldown_until = now + timedelta(seconds=self._cfg.new_order_time_s)
                    st.last_order_fingerprint = fp
                    st.last_order_ts = now

                    st.so_index += 1
                    st.last_anchor_price = mark_price

                    coid = f"{self._bot_id}-avg-mkt-{symbol}-{position_side}-so{st.so_index}".lower()
                    req = NormalizedOrderRequest(
                        exchange=self._exchange,
                        symbol=symbol,
                        type="market",
                        side=side,  # type: ignore[arg-type]
                        position_mode=self._position_mode,
                        position_side=position_side,
                        amount=amount,
                        price=None,
                        reduce_only=False,
                        client_order_id=coid,
                        extra={
                            "trigger": "dynamic_averaging",
                            "mark_price": str(mark_price),
                            "level_price": str(level),
                        },
                    )
                    self._enqueue(key, req)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Averaging monitor failed",
                extra={"symbol": symbol, "position_side": position_side, "monitor_id": monitor_id},
            )
            await asyncio.sleep(1.0)
