from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


def ema(values: Sequence[Decimal], *, length: int) -> list[Decimal]:
    """Simple EMA implementation over Decimal series.

    Returns full-length EMA series (same length as input).
    Uses SMA seed for the first EMA point once enough values exist.
    """
    if length <= 0:
        raise ValueError("length must be > 0")
    if len(values) == 0:
        return []

    k = Decimal("2") / (Decimal(length) + Decimal("1"))
    out: list[Decimal] = []

    sma_sum = Decimal("0")
    ema_prev: Decimal | None = None

    for i, v in enumerate(values):
        if i < length:
            sma_sum += v

        if i == length - 1:
            ema_prev = sma_sum / Decimal(length)
            out.append(ema_prev)
            continue

        if i < length - 1:
            out.append(v)  # placeholder until ema_prev is ready
            continue

        assert ema_prev is not None
        ema_prev = (v - ema_prev) * k + ema_prev
        out.append(ema_prev)

    return out


def sma(values: Sequence[Decimal], *, length: int) -> list[Decimal]:
    if length <= 0:
        raise ValueError("length must be > 0")
    if not values:
        return []
    out: list[Decimal] = []
    s = Decimal("0")
    for i, v in enumerate(values):
        s += v
        if i >= length:
            s -= values[i - length]
        if i < length - 1:
            out.append(v)  # warmup placeholder
        else:
            out.append(s / Decimal(length))
    return out


def _mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("mean of empty")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _abs(x: Decimal) -> Decimal:
    return x.copy_abs()


def rsi(closes: Sequence[Decimal], *, length: int) -> list[Decimal]:
    """Wilder RSI (returns full-length list, warmup placeholders until ready)."""
    if length <= 0:
        raise ValueError("length must be > 0")
    if not closes:
        return []

    out: list[Decimal] = []
    gains: list[Decimal] = []
    losses: list[Decimal] = []

    for i in range(len(closes)):
        if i == 0:
            out.append(Decimal("50"))
            continue

        change = closes[i] - closes[i - 1]
        gains.append(change if change > 0 else Decimal("0"))
        losses.append((-change) if change < 0 else Decimal("0"))

        if len(gains) < length:
            out.append(Decimal("50"))
            continue

        if len(gains) == length:
            avg_gain = _mean(gains[-length:])
            avg_loss = _mean(losses[-length:])
        else:
            # Wilder smoothing
            prev_avg_gain = out_avg_gain
            prev_avg_loss = out_avg_loss
            avg_gain = (prev_avg_gain * (Decimal(length - 1)) + gains[-1]) / Decimal(length)
            avg_loss = (prev_avg_loss * (Decimal(length - 1)) + losses[-1]) / Decimal(length)

        out_avg_gain = avg_gain
        out_avg_loss = avg_loss

        if avg_loss == 0:
            out.append(Decimal("100"))
        else:
            rs = avg_gain / avg_loss
            out.append(Decimal("100") - (Decimal("100") / (Decimal("1") + rs)))

    return out


def stoch_k(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    *,
    k_period: int,
) -> list[Decimal]:
    """Fast %K (0..100). Warmup placeholders until ready."""
    if k_period <= 0:
        raise ValueError("k_period must be > 0")
    n = min(len(highs), len(lows), len(closes))
    if n == 0:
        return []

    out: list[Decimal] = []
    for i in range(n):
        if i < k_period - 1:
            out.append(Decimal("50"))
            continue
        hh = max(highs[i - k_period + 1 : i + 1])
        ll = min(lows[i - k_period + 1 : i + 1])
        denom = hh - ll
        if denom == 0:
            out.append(Decimal("50"))
            continue
        out.append((closes[i] - ll) / denom * Decimal("100"))
    return out


def stoch(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    *,
    fastk_period: int,
    slowk_period: int,
    slowd_period: int,
) -> tuple[list[Decimal], list[Decimal]]:
    """Stochastic oscillator (slowK, slowD)."""
    fast_k = stoch_k(highs, lows, closes, k_period=fastk_period)
    slow_k = sma(fast_k, length=slowk_period)
    slow_d = sma(slow_k, length=slowd_period)
    return slow_k, slow_d


def cci(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    *,
    period: int,
) -> list[Decimal]:
    """CCI based on Typical Price (H+L+C)/3. Warmup placeholders until ready."""
    if period <= 0:
        raise ValueError("period must be > 0")
    n = min(len(highs), len(lows), len(closes))
    if n == 0:
        return []

    tp = [(highs[i] + lows[i] + closes[i]) / Decimal("3") for i in range(n)]
    out: list[Decimal] = []
    for i in range(n):
        if i < period - 1:
            out.append(Decimal("0"))
            continue
        window = tp[i - period + 1 : i + 1]
        sma_tp = _mean(window)
        md = _mean([_abs(x - sma_tp) for x in window])
        if md == 0:
            out.append(Decimal("0"))
            continue
        out.append((tp[i] - sma_tp) / (Decimal("0.015") * md))
    return out


@dataclass(frozen=True, slots=True)
class CrossSignal:
    side: str  # "long" | "short" | "none"
    fast: Decimal
    slow: Decimal
    prev_fast: Decimal
    prev_slow: Decimal


def cross_signal(fast_series: Sequence[Decimal], slow_series: Sequence[Decimal]) -> CrossSignal | None:
    """Generic cross detector on last 2 points."""
    if len(fast_series) < 2 or len(slow_series) < 2:
        return None
    fast = fast_series[-1]
    slow = slow_series[-1]
    prev_fast = fast_series[-2]
    prev_slow = slow_series[-2]

    if prev_fast <= prev_slow and fast > slow:
        side = "long"
    elif prev_fast >= prev_slow and fast < slow:
        side = "short"
    else:
        side = "none"
    return CrossSignal(side=side, fast=fast, slow=slow, prev_fast=prev_fast, prev_slow=prev_slow)


@dataclass(frozen=True, slots=True)
class MACrossSignal:
    side: str  # "long" | "short" | "none"
    fast: Decimal
    slow: Decimal
    prev_fast: Decimal
    prev_slow: Decimal


def ma_cross_signal(
    closes: Sequence[Decimal],
    *,
    fast_len: int,
    slow_len: int,
) -> MACrossSignal | None:
    if len(closes) < max(fast_len, slow_len) + 2:
        return None

    fast_series = ema(closes, length=fast_len)
    slow_series = ema(closes, length=slow_len)

    sig = cross_signal(fast_series, slow_series)
    if sig is None:
        return None
    return MACrossSignal(
        side=sig.side,
        fast=sig.fast,
        slow=sig.slow,
        prev_fast=sig.prev_fast,
        prev_slow=sig.prev_slow,
    )


def level_cross_signal(values: Sequence[Decimal], *, long_level: Decimal, short_level: Decimal) -> str:
    """Crossing a horizontal level:
    - LONG: cross up through long_level
    - SHORT: cross down through short_level
    """
    if len(values) < 2:
        return "none"
    prev_v = values[-2]
    v = values[-1]
    if prev_v <= long_level and v > long_level:
        return "long"
    if prev_v >= short_level and v < short_level:
        return "short"
    return "none"
