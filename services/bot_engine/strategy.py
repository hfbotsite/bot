from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping, Sequence

from services.bot_runtime.price_feed import PriceFeed
from services.bot_runtime.settings import BotSettings
from services.bot_runtime.signal_store import SignalStore
from services.execution.models import NormalizedOrderRequest, PositionSide

from .position_math import build_grid_levels, select_active_grid_indices


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    desired_orders: list[NormalizedOrderRequest]


def _parse_percent(s: str) -> Decimal:
    """Parse a percent-like config value into a fraction.

    Supported:
      - "0.3%" -> 0.003
      - "0.3"  -> 0.003   (treat as percent for legacy JSON)
      - "0.003" -> 0.00003 (still treated as percent; avoid this in configs)

    NOTE: Our legacy JSON uses numeric strings like "0.3" to mean 0.3%.
    """
    raw = s.strip()
    if raw.endswith("%"):
        return Decimal(raw[:-1].strip()) / Decimal("100")
    return Decimal(raw) / Decimal("100")


def _tp_price(*, avg_entry: Decimal, position_side: PositionSide, tp_pct: Decimal) -> Decimal:
    if position_side == "LONG":
        return avg_entry * (Decimal("1") + tp_pct)
    if position_side == "SHORT":
        return avg_entry * (Decimal("1") - tp_pct)
    raise ValueError("tp requires LONG|SHORT")


def _sl_price(*, avg_entry: Decimal, position_side: PositionSide, sl_pct: Decimal) -> Decimal:
    # sl_pct is a fraction (0.01 => 1%)
    if sl_pct <= 0:
        raise ValueError("sl_pct must be > 0")
    if position_side == "LONG":
        return avg_entry * (Decimal("1") - sl_pct)
    if position_side == "SHORT":
        return avg_entry * (Decimal("1") + sl_pct)
    raise ValueError("sl requires LONG|SHORT")


def _squeeze_price(*, tp_price: Decimal, position_side: PositionSide, squeeze_pct: Decimal) -> Decimal:
    # squeeze_pct is a fraction (0.01 => 1%)
    if squeeze_pct <= 0:
        raise ValueError("squeeze_pct must be > 0")
    if position_side == "LONG":
        return tp_price * (Decimal("1") + squeeze_pct)
    if position_side == "SHORT":
        return tp_price * (Decimal("1") - squeeze_pct)
    raise ValueError("squeeze requires LONG|SHORT")


def _grid_price_ref(price_feed: PriceFeed, symbol: str) -> Decimal:
    # MVP: take best available from price feed (implementation-defined).
    # We keep it in one place to adjust later (Mark vs Last).
    tick = price_feed.latest_price(symbol=symbol)
    if tick is None:
        raise RuntimeError("No price for grid reference")
    return tick.price


class StrategySupervisor:
    """MVP strategy supervisor.

    Scope (MVP):
      - computes desired TP reduceOnly conditional order based on WA avg entry
      - entry/grid logic will be added next (incrementally)

    IMPORTANT: This module only produces desired orders; execution/reconcile is done elsewhere.
    """

    def __init__(self, *, settings: BotSettings, price_feed: PriceFeed, signals: SignalStore):
        self._settings = settings
        self._price_feed = price_feed
        self._signals = signals

    def decide(
        self,
        *,
        symbol: str,
        position_side: PositionSide,
        position_qty: Decimal,
        avg_entry_price: Decimal | None,
        open_orders: Sequence[Mapping[str, object]] = (),
    ) -> StrategyDecision:
        desired: list[NormalizedOrderRequest] = []

        # --- ENTRY ---
        # If no position yet:
        # - if entry_by_indicators: place grid BO/SO only when entry signal matches position_side.
        # - else: enter by market when filters pass (EMA200 / Global STOCH), then continue grid from avg entry.
        if position_qty == 0 or avg_entry_price is None:
            # Indicator-gated entry
            if self._settings.entry.entry_by_indicators:
                sig = self._signals.get(symbol=symbol, event="entry")
                if sig is None or sig.side == "none":
                    return StrategyDecision(desired_orders=[])
                if position_side == "LONG" and sig.side != "long":
                    return StrategyDecision(desired_orders=[])
                if position_side == "SHORT" and sig.side != "short":
                    return StrategyDecision(desired_orders=[])

            # If entry_by_indicators is disabled, we will allow entry if filters are disabled or pass.
            # MVP: treat disabled filters as pass; real filter computation will be added later.
            if not self._settings.entry.entry_by_indicators:
                # NOTE: filters live in indicators_tuning (use_ema200/use_global_stoch). If both enabled,
                # we should compute them from global_timeframe candles (not implemented yet) -> allow only if pass.
                # For now we allow if any filter is disabled (common during setup) or both disabled.
                if self._settings.indicators_tuning.use_ema200 or self._settings.indicators_tuning.use_global_stoch:
                    # Placeholder: until global filters are implemented, do not enter.
                    return StrategyDecision(desired_orders=[])

                entry_price = _grid_price_ref(self._price_feed, symbol)
                side = "buy" if position_side == "LONG" else "sell"
                coid = f"{self._settings.bot_id}-entry-mkt-{symbol}-{position_side}".lower()
                desired.append(
                    NormalizedOrderRequest(
                        exchange=self._settings.bot.exchange,
                        symbol=symbol,
                        type="market",
                        side=side,  # type: ignore[arg-type]
                        position_mode=self._settings.position_mode,
                        position_side=position_side,
                        amount=self._settings.basic.bo_amount,
                        price=None,
                        reduce_only=False,
                        client_order_id=coid,
                        extra={},
                    )
                )
                return StrategyDecision(desired_orders=desired)

            entry_price = _grid_price_ref(self._price_feed, symbol)

            first_step_pct = Decimal(str(self._settings.grid.first_step)) / Decimal("100")
            range_cover_pct = Decimal(str(self._settings.grid.range_cover)) / Decimal("100")

            levels = build_grid_levels(
                position_side=position_side,
                entry_price=entry_price,
                bo_amount=self._settings.basic.bo_amount,
                orders_total=self._settings.basic.orders_total,
                first_step_pct=first_step_pct,
                range_cover_pct=range_cover_pct,
                first_so_coeff=self._settings.grid.first_so_coeff,
                dynamic_so_coeff=self._settings.grid.dynamic_so_coeff,
                martingale=self._settings.grid.martingale,
            )

            active = select_active_grid_indices(
                filled_levels=0,
                orders_total=self._settings.basic.orders_total,
                active_orders=self._settings.basic.active_orders,
            )

            for i in active:
                lvl = levels[i]
                side = "buy" if position_side == "LONG" else "sell"
                coid = f"{self._settings.bot_id}-grid-{symbol}-{position_side}-{lvl.index}".lower()
                desired.append(
                    NormalizedOrderRequest(
                        exchange=self._settings.bot.exchange,
                        symbol=symbol,
                        type="limit",
                        side=side,  # type: ignore[arg-type]
                        position_mode=self._settings.position_mode,
                        position_side=position_side,
                        amount=lvl.amount,
                        price=lvl.price,
                        reduce_only=False,
                        client_order_id=coid,
                        extra={},
                    )
                )

            return StrategyDecision(desired_orders=desired)

        # --- EXIT MODE selector ---
        # settings.exit.take_profit:
        # - "profit_exit" => use squeeze/tp/sl logic (baseline)
        # - "indicators_exit" => close by indicator signal, do NOT create profit exit orders
        exit_mode = (str(self._settings.exit.take_profit) or "profit_exit").lower()

        if exit_mode == "indicators_exit":
            exit_sig = self._signals.get(symbol=symbol, event="exit")
            if exit_sig is not None and exit_sig.side != "none":
                # exit_sig.side is expressed in long/short direction; for closing we map:
                # - if we are LONG and signal says "short" => close LONG
                # - if we are SHORT and signal says "long" => close SHORT
                should_close = (position_side == "LONG" and exit_sig.side == "short") or (
                    position_side == "SHORT" and exit_sig.side == "long"
                )
                if should_close:
                    close_side = "sell" if position_side == "LONG" else "buy"
                    preset = (exit_sig.preset or "unknown").lower()
                    coid = f"{self._settings.bot_id}-exit-ind-{preset}-{symbol}-{position_side}".lower()
                    desired.append(
                        NormalizedOrderRequest(
                            exchange=self._settings.bot.exchange,
                            symbol=symbol,
                            type="market",
                            side=close_side,  # type: ignore[arg-type]
                            position_mode=self._settings.position_mode,
                            position_side=position_side,
                            amount=position_qty,
                            price=None,
                            reduce_only=True,
                            client_order_id=coid,
                            extra={},
                        )
                    )
            return StrategyDecision(desired_orders=desired)

        # --- EXIT (profit_exit): squeeze + TP-market fallback + stop-loss ---
        # Config units:
        # - exit_profit_level: percent (0.3 => 0.3%)
        # - squeeze_profit: percent (4.2 => 4.2%) - if 0 => disabled
        # - exit_stop_loss_level: percent (2.2 => 2.2%) - if 0 => disabled
        tp_pct = _parse_percent(str(self._settings.exit.exit_profit_level))
        tp_price = _tp_price(avg_entry=avg_entry_price, position_side=position_side, tp_pct=tp_pct)

        tp_side = "sell" if position_side == "LONG" else "buy"

        # SQUEEZE limit: above TP for LONG, below TP for SHORT
        squeeze_pct_raw = Decimal(str(self._settings.exit.squeeze_profit))
        if squeeze_pct_raw > 0:
            squeeze_pct = squeeze_pct_raw / Decimal("100")
            squeeze_price = _squeeze_price(tp_price=tp_price, position_side=position_side, squeeze_pct=squeeze_pct)
            squeeze_coid = f"{self._settings.bot_id}-squeeze-{symbol}-{position_side}".lower()
            desired.append(
                NormalizedOrderRequest(
                    exchange=self._settings.bot.exchange,
                    symbol=symbol,
                    type="limit",
                    side=tp_side,  # type: ignore[arg-type]
                    position_mode=self._settings.position_mode,
                    position_side=position_side,
                    amount=position_qty,
                    price=squeeze_price,
                    reduce_only=True,
                    client_order_id=squeeze_coid,
                    extra={},
                )
            )

        # TP fallback: MARKET when trigger hits (if squeeze wasn't filled).
        # We implement it as a conditional "take_profit" with market execution (price=None).
        trigger_direction_tp = 1 if position_side == "LONG" else 2
        tp_coid = f"{self._settings.bot_id}-tp-{symbol}-{position_side}".lower()
        desired.append(
            NormalizedOrderRequest(
                exchange=self._settings.bot.exchange,
                symbol=symbol,
                type="take_profit",
                side=tp_side,  # type: ignore[arg-type]
                position_mode=self._settings.position_mode,
                position_side=position_side,
                amount=position_qty,
                price=None,
                reduce_only=True,
                client_order_id=tp_coid,
                extra={
                    "triggerPrice": tp_price,
                    "triggerDirection": trigger_direction_tp,
                    "triggerBy": "MarkPrice",
                },
            )
        )

        # Stop-loss (optional): MARKET on adverse move from avg entry.
        sl_pct_raw = Decimal(str(self._settings.exit.exit_stop_loss_level))
        if sl_pct_raw > 0:
            sl_pct = sl_pct_raw / Decimal("100")
            sl_trigger_price = _sl_price(avg_entry=avg_entry_price, position_side=position_side, sl_pct=sl_pct)
            trigger_direction_sl = 2 if position_side == "LONG" else 1
            sl_coid = f"{self._settings.bot_id}-sl-{symbol}-{position_side}".lower()
            desired.append(
                NormalizedOrderRequest(
                    exchange=self._settings.bot.exchange,
                    symbol=symbol,
                    type="stop",
                    side=tp_side,  # type: ignore[arg-type]
                    position_mode=self._settings.position_mode,
                    position_side=position_side,
                    amount=position_qty,
                    price=None,
                    reduce_only=True,
                    client_order_id=sl_coid,
                    extra={
                        "triggerPrice": sl_trigger_price,
                        "triggerDirection": trigger_direction_sl,
                        "triggerBy": "MarkPrice",
                    },
                )
            )

        # --- GRID continuation (baseline) ---
        # MVP: assume at least BO filled once position exists; start from level=1.
        entry_price = avg_entry_price
        first_step_pct = Decimal(str(self._settings.grid.first_step)) / Decimal("100")
        range_cover_pct = Decimal(str(self._settings.grid.range_cover)) / Decimal("100")

        levels = build_grid_levels(
            position_side=position_side,
            entry_price=entry_price,
            bo_amount=self._settings.basic.bo_amount,
            orders_total=self._settings.basic.orders_total,
            first_step_pct=first_step_pct,
            range_cover_pct=range_cover_pct,
            first_so_coeff=self._settings.grid.first_so_coeff,
            dynamic_so_coeff=self._settings.grid.dynamic_so_coeff,
            martingale=self._settings.grid.martingale,
        )

        active = select_active_grid_indices(
            filled_levels=1,
            orders_total=self._settings.basic.orders_total,
            active_orders=self._settings.basic.active_orders,
        )

        for i in active:
            if i <= 0:
                continue
            lvl = levels[i]
            side = "buy" if position_side == "LONG" else "sell"
            coid = f"{self._settings.bot_id}-grid-{symbol}-{position_side}-{lvl.index}".lower()
            desired.append(
                NormalizedOrderRequest(
                    exchange=self._settings.bot.exchange,
                    symbol=symbol,
                    type="limit",
                    side=side,  # type: ignore[arg-type]
                    position_mode=self._settings.position_mode,
                    position_side=position_side,
                    amount=lvl.amount,
                    price=lvl.price,
                    reduce_only=False,
                    client_order_id=coid,
                    extra={},
                )
            )

        return StrategyDecision(desired_orders=desired)
