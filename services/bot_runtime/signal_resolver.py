from __future__ import annotations

from decimal import Decimal
from typing import Literal

from .candle_store import CandleStore
from .indicators import cci, cross_signal, ema, level_cross_signal, rsi, sma, stoch
from .signal_store import SignalSide, SignalStore
from .settings import (
    AveragingConfig,
    BotSettings,
    EntryConfig,
    ExitConfig,
    PresetCciCrossConfig,
    PresetMaCrossConfig,
    PresetRsiSmaRsiCrossConfig,
    PresetStochCciConfig,
    PresetStochRsiConfig,
)


EventKind = Literal["entry", "averaging", "exit"]


def _closes(store: CandleStore, *, symbol: str, timeframe: str) -> list[Decimal]:
    candles = store.list(symbol=symbol, timeframe=timeframe)
    return [c.close for c in candles]


def _highs(store: CandleStore, *, symbol: str, timeframe: str) -> list[Decimal]:
    candles = store.list(symbol=symbol, timeframe=timeframe)
    return [c.high for c in candles]


def _lows(store: CandleStore, *, symbol: str, timeframe: str) -> list[Decimal]:
    candles = store.list(symbol=symbol, timeframe=timeframe)
    return [c.low for c in candles]




def _invert_for_exit(side: SignalSide) -> SignalSide:
    if side == "long":
        return "short"
    if side == "short":
        return "long"
    return "none"


def _ma_cross(closes: list[Decimal], cfg: PresetMaCrossConfig) -> tuple[SignalSide, dict[str, object]]:
    if len(closes) < max(cfg.ma1_length, cfg.ma2_length) + 2:
        return "none", {"warmup": True}
    fast = ema(closes, length=cfg.ma1_length)
    slow = ema(closes, length=cfg.ma2_length)
    sig = cross_signal(fast, slow)
    if sig is None:
        return "none", {"warmup": True}
    return sig.side, {"fast": str(sig.fast), "slow": str(sig.slow)}


def _cci_cross(values: list[Decimal], cfg: PresetCciCrossConfig, *, for_exit: bool) -> tuple[SignalSide, dict[str, object]]:
    # Entry/Averaging: long = cross up long_level; short = cross down short_level
    # Exit: opposite.
    if len(values) < 2:
        return "none", {"warmup": True}
    if not for_exit:
        side = level_cross_signal(values, long_level=cfg.cci_long_level, short_level=cfg.cci_short_level)
    else:
        side = level_cross_signal(values, long_level=cfg.cci_short_level, short_level=cfg.cci_long_level)
    return side, {"cci": str(values[-1])}


def _rsi_smarsi_cross(values: list[Decimal], cfg: PresetRsiSmaRsiCrossConfig, *, for_exit: bool) -> tuple[SignalSide, dict[str, object]]:
    if len(values) < max(cfg.rsi_period, cfg.smarsi_length) + 2:
        return "none", {"warmup": True}

    r = rsi(values, length=cfg.rsi_period)
    s = sma(r, length=cfg.smarsi_length)
    sig = cross_signal(r, s)
    if sig is None:
        return "none", {"warmup": True}

    side: SignalSide = sig.side
    if for_exit:
        side = _invert_for_exit(side)

    return side, {"rsi": str(sig.fast), "smarsi": str(sig.slow)}


def _stoch_cci(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    cfg: PresetStochCciConfig,
    *,
    for_exit: bool,
) -> tuple[SignalSide, dict[str, object]]:
    # Crossover semantics:
    # - Primary cross: slowK vs slowD (fast=slowK, slow=slowD)
    # - For entry/avg:
    #    long when K crosses D up while in "oversold" (<= long_up_level)
    #    short when K crosses D down while in "overbought" (>= short_low_level)
    # - For exit: reverse of entry (as per user requirement)
    if min(len(highs), len(lows), len(closes)) < cfg.stoch_fastk_period + cfg.stoch_slowk_period + cfg.stoch_slowd_period + 2:
        return "none", {"warmup": True}

    k, d = stoch(
        highs,
        lows,
        closes,
        fastk_period=cfg.stoch_fastk_period,
        slowk_period=cfg.stoch_slowk_period,
        slowd_period=cfg.stoch_slowd_period,
    )
    cs = cross_signal(k, d)
    if cs is None:
        return "none", {"warmup": True}

    stoch_now = k[-1]
    side: SignalSide = "none"

    if not for_exit:
        # Entry/avg
        if cs.side == "long" and stoch_now <= cfg.stoch_long_up_level:
            side = "long"
        elif cs.side == "short" and stoch_now >= cfg.stoch_short_low_level:
            side = "short"
    else:
        # Exit opposite
        if cs.side == "short" and stoch_now >= cfg.stoch_long_low_level:
            side = "long"  # close SHORT (signal long)
        elif cs.side == "long" and stoch_now <= cfg.stoch_short_up_level:
            side = "short"  # close LONG (signal short)

    return side, {"k": str(k[-1]), "d": str(d[-1])}


def _stoch_rsi(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    cfg: PresetStochRsiConfig,
    *,
    for_exit: bool,
) -> tuple[SignalSide, dict[str, object]]:
    # We implement RSI cross-level as primary, and optional stoch filter.
    # If basic_indicator == "rsi": detect RSI crossing rsi_long_level / rsi_short_level.
    if len(closes) < cfg.rsi_period + 2:
        return "none", {"warmup": True}

    r = rsi(closes, length=cfg.rsi_period)
    if not for_exit:
        side = level_cross_signal(r, long_level=cfg.rsi_long_level, short_level=cfg.rsi_short_level)
    else:
        # reverse for exit
        side = level_cross_signal(r, long_level=cfg.rsi_short_level, short_level=cfg.rsi_long_level)

    detail: dict[str, object] = {"rsi": str(r[-1])}

    if cfg.use_stoch:
        if min(len(highs), len(lows), len(closes)) < cfg.stoch_fastk_period + cfg.stoch_slowk_period + cfg.stoch_slowd_period + 2:
            return "none", {"warmup": True}
        k, d = stoch(
            highs,
            lows,
            closes,
            fastk_period=cfg.stoch_fastk_period,
            slowk_period=cfg.stoch_slowk_period,
            slowd_period=cfg.stoch_slowd_period,
        )
        detail["k"] = str(k[-1])
        detail["d"] = str(d[-1])

    return side, detail


def resolve_entry_signal(settings: BotSettings, store: CandleStore, *, symbol: str) -> tuple[SignalSide, str, dict[str, object]]:
    cfg: EntryConfig = settings.entry
    preset = (cfg.entry_preset or "NONE").upper()
    tf = cfg.entry_timeframe

    closes = _closes(store, symbol=symbol, timeframe=tf)
    highs = _highs(store, symbol=symbol, timeframe=tf)
    lows = _lows(store, symbol=symbol, timeframe=tf)

    if preset == "MA_CROSS":
        side, detail = _ma_cross(closes, cfg.ma_cross)
        return side, preset, detail
    if preset == "STOCH_CCI":
        side, detail = _stoch_cci(highs, lows, closes, cfg.stoch_cci, for_exit=False)
        return side, preset, detail
    if preset == "STOCH_RSI":
        side, detail = _stoch_rsi(highs, lows, closes, cfg.stoch_rsi, for_exit=False)
        return side, preset, detail
    if preset == "CCI_CROSS":
        series = cci(highs, lows, closes, period=cfg.cci_cross.cci_period)
        side, detail = _cci_cross(series, cfg.cci_cross, for_exit=False)
        return side, preset, detail
    if preset == "RSI_SMARSI_CROSS":
        side, detail = _rsi_smarsi_cross(closes, cfg.rsi_smarsi_cross, for_exit=False)
        return side, preset, detail

    return "none", preset, {"unsupported_preset": preset}


def resolve_averaging_signal(settings: BotSettings, store: CandleStore, *, symbol: str) -> tuple[SignalSide, str, dict[str, object]]:
    cfg: AveragingConfig = settings.averaging
    preset = (cfg.avg_preset or "NONE").upper()
    tf = cfg.timeframe

    closes = _closes(store, symbol=symbol, timeframe=tf)
    highs = _highs(store, symbol=symbol, timeframe=tf)
    lows = _lows(store, symbol=symbol, timeframe=tf)

    if preset == "MA_CROSS":
        side, detail = _ma_cross(closes, cfg.ma_cross)
        return side, preset, detail
    if preset == "STOCH_CCI":
        side, detail = _stoch_cci(highs, lows, closes, cfg.stoch_cci, for_exit=False)
        return side, preset, detail
    if preset == "STOCH_RSI":
        side, detail = _stoch_rsi(highs, lows, closes, cfg.stoch_rsi, for_exit=False)
        return side, preset, detail
    if preset == "CCI_CROSS":
        series = cci(highs, lows, closes, period=cfg.cci_cross.cci_period)
        side, detail = _cci_cross(series, cfg.cci_cross, for_exit=False)
        return side, preset, detail
    if preset == "RSI_SMARSI_CROSS":
        side, detail = _rsi_smarsi_cross(closes, cfg.rsi_smarsi_cross, for_exit=False)
        return side, preset, detail

    return "none", preset, {"unsupported_preset": preset}


def resolve_exit_signal(settings: BotSettings, store: CandleStore, *, symbol: str) -> tuple[SignalSide, str, dict[str, object]]:
    cfg: ExitConfig = settings.exit
    preset = (cfg.exit_preset or "NONE").upper()
    tf = cfg.exit_timeframe

    closes = _closes(store, symbol=symbol, timeframe=tf)
    highs = _highs(store, symbol=symbol, timeframe=tf)
    lows = _lows(store, symbol=symbol, timeframe=tf)

    if preset == "NONE":
        return "none", preset, {}

    if preset == "MA_CROSS":
        side, detail = _ma_cross(closes, cfg.ma_cross)
        side = _invert_for_exit(side)
        return side, preset, detail
    if preset == "STOCH_CCI":
        side, detail = _stoch_cci(highs, lows, closes, cfg.stoch_cci, for_exit=True)
        return side, preset, detail
    if preset == "STOCH_RSI":
        side, detail = _stoch_rsi(highs, lows, closes, cfg.stoch_rsi, for_exit=True)
        return side, preset, detail
    if preset == "CCI_CROSS":
        series = cci(highs, lows, closes, period=cfg.cci_cross.cci_period)
        side, detail = _cci_cross(series, cfg.cci_cross, for_exit=True)
        return side, preset, detail
    if preset == "RSI_SMARSI_CROSS":
        side, detail = _rsi_smarsi_cross(closes, cfg.rsi_smarsi_cross, for_exit=True)
        return side, preset, detail

    return "none", preset, {"unsupported_preset": preset}


def recompute_all(settings: BotSettings, store: CandleStore, signals: SignalStore, *, symbol: str) -> None:
    entry_side, entry_preset, entry_detail = resolve_entry_signal(settings, store, symbol=symbol)
    signals.set(symbol=symbol, event="entry", side=entry_side, preset=entry_preset, detail=entry_detail)

    if settings.averaging.enabled:
        avg_side, avg_preset, avg_detail = resolve_averaging_signal(settings, store, symbol=symbol)
        signals.set(symbol=symbol, event="averaging", side=avg_side, preset=avg_preset, detail=avg_detail)

    exit_side, exit_preset, exit_detail = resolve_exit_signal(settings, store, symbol=symbol)
    signals.set(symbol=symbol, event="exit", side=exit_side, preset=exit_preset, detail=exit_detail)
