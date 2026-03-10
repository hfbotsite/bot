from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from .events import PositionSide, Side


FillEffect = Literal["increase", "reduce", "flip"]


@dataclass(frozen=True, slots=True)
class GridLevel:
    index: int
    price: Decimal
    amount: Decimal


@dataclass(slots=True)
class PositionState:
    """In-memory position state (MVP).

    qty is signed in the internal engine convention:
    - LONG: qty > 0
    - SHORT: qty > 0 (but interpreted as short exposure when position_side=SHORT)

    For one-way we treat qty sign by buy/sell (positive/negative) via signed_qty().
    """

    qty: Decimal = Decimal("0")
    avg_entry_price: Decimal | None = None
    realized_pnl_gross: Decimal = Decimal("0")


def signed_qty(side: Side, position_side: PositionSide, qty: Decimal) -> Decimal:
    """Convert exchange-side qty into signed qty for engine calculations."""

    if qty < 0:
        raise ValueError("qty must be >= 0")

    if position_side == "LONG":
        return qty if side == "buy" else -qty

    if position_side == "SHORT":
        # In hedge mode, opening short is SELL (+), closing short is BUY (-)
        return qty if side == "sell" else -qty

    # ONE_WAY
    return qty if side == "buy" else -qty


def classify_fill_effect(current_qty: Decimal, delta_qty: Decimal) -> FillEffect:
    """Classify how delta affects current position.

    current_qty and delta_qty are signed in the same convention (ONE_WAY).
    """

    if current_qty == 0:
        return "increase" if delta_qty != 0 else "increase"

    # Same direction => increase
    if (current_qty > 0 and delta_qty > 0) or (current_qty < 0 and delta_qty < 0):
        return "increase"

    # Opposite direction: reduce or flip
    new_qty = current_qty + delta_qty
    if new_qty == 0 or (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0):
        return "reduce"

    return "flip"


def _realized_pnl_gross_for_close(
    position_side: PositionSide,
    avg_entry_price: Decimal,
    exit_price: Decimal,
    closed_qty_abs: Decimal,
) -> Decimal:
    """Compute realized PnL (gross) for the closing part.

    closed_qty_abs is always positive.

    LONG:  pnl = (exit - entry) * qty
    SHORT: pnl = (entry - exit) * qty
    """

    if closed_qty_abs < 0:
        raise ValueError("closed_qty_abs must be >= 0")

    if position_side == "LONG" or position_side == "ONE_WAY":
        return (exit_price - avg_entry_price) * closed_qty_abs

    # SHORT
    return (avg_entry_price - exit_price) * closed_qty_abs


def build_grid_levels(
    *,
    position_side: PositionSide,
    entry_price: Decimal,
    bo_amount: Decimal,
    orders_total: int,
    first_step_pct: Decimal,
    range_cover_pct: Decimal,
    first_so_coeff: Decimal,
    dynamic_so_coeff: Decimal,
    martingale: Decimal,
) -> list[GridLevel]:
    """Build BO+SO grid levels for one position side (hedge).

    Conventions:
      - first_step_pct/range_cover_pct are fractions: 0.005 means 0.5%
      - LONG grid prices go down from entry; SHORT grid prices go up from entry
      - amount is in base units (as provided by config)

    NOTE: This is a deterministic math helper; no I/O and no rounding to exchange filters yet.
    """
    if orders_total < 1:
        raise ValueError("orders_total must be >= 1")
    if bo_amount <= 0:
        raise ValueError("bo_amount must be > 0")
    if first_step_pct <= 0:
        raise ValueError("first_step_pct must be > 0")
    if range_cover_pct <= 0:
        raise ValueError("range_cover_pct must be > 0")

    # Distribute prices over [first_step .. range_cover] inclusive.
    # For now use linear spacing in percentage space (simple baseline).
    if orders_total == 1:
        step_pcts = [first_step_pct]
    else:
        span = range_cover_pct - first_step_pct
        if span < 0:
            raise ValueError("range_cover_pct must be >= first_step_pct")
        step_pcts = [
            first_step_pct + (span * Decimal(i) / Decimal(orders_total - 1)) for i in range(orders_total)
        ]

    levels: list[GridLevel] = []
    for i, step_pct in enumerate(step_pcts):
        if position_side == "LONG":
            price = entry_price * (Decimal("1") - step_pct)
        elif position_side == "SHORT":
            price = entry_price * (Decimal("1") + step_pct)
        else:
            raise ValueError("grid requires LONG|SHORT")

        if i == 0:
            amount = bo_amount
        else:
            # baseline: SO amount = bo_amount * first_so_coeff * (dynamic_so_coeff ** (i-1)) * (martingale ** (i-1))
            # (kept explicit for readability; can be adjusted to match legacy exact formula later)
            scale = first_so_coeff * (dynamic_so_coeff ** Decimal(i - 1)) * (martingale ** Decimal(i - 1))
            amount = bo_amount * scale

        levels.append(GridLevel(index=i, price=price, amount=amount))

    return levels


def select_active_grid_indices(*, filled_levels: int, orders_total: int, active_orders: int) -> list[int]:
    """Return grid indices that should be kept on exchange.

    - filled_levels: how many levels already executed/consumed (0 means none yet)
    - active_orders=0 => keep only next one (filled_levels as next index for FLAT is 0)
    - active_orders>0 => keep up to N starting from filled_levels

    Example (active_orders=2, filled_levels=1) => [1,2]
    """
    if orders_total < 1:
        return []
    start = max(0, filled_levels)
    if start >= orders_total:
        return []

    if active_orders <= 0:
        return [start]

    end = min(orders_total, start + active_orders)
    return list(range(start, end))


def apply_fill_wa(
    state: PositionState,
    *,
    position_side: PositionSide,
    delta_qty: Decimal,
    price: Decimal,
) -> tuple[PositionState, Decimal, Decimal]:
    """Apply a signed qty change to position state using Weighted Average.

    Parameters:
      - state: current PositionState
      - position_side: LONG/SHORT/ONE_WAY (defines realized PnL sign rules)
      - delta_qty: signed delta in ONE_WAY convention
      - price: execution price for this delta

    Flip handling (MVP): split into close-to-zero + open remainder.

    Returns:
      (new_state, closed_qty_abs, realized_delta)
    where:
      - closed_qty_abs: how much was closed by this fill (abs qty)
      - realized_delta: realized PnL (gross) generated by this fill
    """

    if delta_qty == 0:
        return state, Decimal("0"), Decimal("0")

    cur_qty = state.qty
    cur_avg = state.avg_entry_price

    # Opening from flat
    if cur_qty == 0:
        new_state = PositionState(qty=delta_qty, avg_entry_price=price, realized_pnl_gross=state.realized_pnl_gross)
        return new_state, Decimal("0"), Decimal("0")

    if cur_avg is None:
        raise ValueError("avg_entry_price must be set when qty != 0")

    effect = classify_fill_effect(cur_qty, delta_qty)

    # Increase: weighted average
    if effect == "increase":
        new_qty = cur_qty + delta_qty
        # WA by notional: (avg*|cur| + price*|delta|) / |new|
        cur_abs = abs(cur_qty)
        delta_abs = abs(delta_qty)
        new_abs = abs(new_qty)
        new_avg = (cur_avg * cur_abs + price * delta_abs) / new_abs
        new_state = PositionState(qty=new_qty, avg_entry_price=new_avg, realized_pnl_gross=state.realized_pnl_gross)
        return new_state, Decimal("0"), Decimal("0")

    # Reduce / Flip
    # Determine closed size: min(|cur|, |delta|)
    cur_abs = abs(cur_qty)
    delta_abs = abs(delta_qty)
    closed_abs = min(cur_abs, delta_abs)

    realized_delta = _realized_pnl_gross_for_close(position_side, cur_avg, price, closed_abs)
    realized_total = state.realized_pnl_gross + realized_delta

    # Remaining qty after applying full delta
    new_qty = cur_qty + delta_qty

    if effect == "reduce":
        if new_qty == 0:
            # Flat => reset avg
            new_state = PositionState(qty=Decimal("0"), avg_entry_price=None, realized_pnl_gross=realized_total)
            return new_state, closed_abs, realized_delta

        # Still same direction => avg stays the same
        new_state = PositionState(qty=new_qty, avg_entry_price=cur_avg, realized_pnl_gross=realized_total)
        return new_state, closed_abs, realized_delta

    # flip: split close-to-zero + open remainder at current price
    remainder_abs = delta_abs - closed_abs
    # new_qty sign is opposite; for WA we reset avg to execution price
    remainder_signed = remainder_abs if new_qty > 0 else -remainder_abs
    new_state = PositionState(qty=remainder_signed, avg_entry_price=price, realized_pnl_gross=realized_total)
    return new_state, closed_abs, realized_delta
