from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from .candle_store import CandleStore
from .indicators import MACrossSignal, ma_cross_signal


logger = logging.getLogger("bot_runtime.indicators")


@dataclass(frozen=True, slots=True)
class IndicatorConfig:
    preset: str = "MA_CROSS"
    fast_len: int = 9
    slow_len: int = 21
    timeframe: str = "1m"


class IndicatorPipeline:
    """Pull-based indicator pipeline (MVP).

    - Reads candles from CandleStore.
    - Recomputes on candle close changes.
    - Emits/logs MA_CROSS signal.
    """

    def __init__(
        self,
        *,
        store: CandleStore,
        symbol: str,
        cfg: IndicatorConfig,
        poll_interval_s: float = 0.5,
    ) -> None:
        self._store = store
        self._symbol = symbol
        self._cfg = cfg
        self._poll_interval_s = float(poll_interval_s)
        self._last_open_time_ms: int | None = None

    def _closes(self) -> list[Decimal]:
        candles = self._store.list(symbol=self._symbol, timeframe=self._cfg.timeframe)
        return [c.close for c in candles]

    async def run(self) -> None:
        while True:
            candle = self._store.latest(symbol=self._symbol, timeframe=self._cfg.timeframe)
            if candle is not None and candle.open_time_ms != self._last_open_time_ms:
                self._last_open_time_ms = candle.open_time_ms
                self._on_new_candle()

            await asyncio.sleep(self._poll_interval_s)

    def _on_new_candle(self) -> None:
        if self._cfg.preset != "MA_CROSS":
            return

        closes = self._closes()
        sig: MACrossSignal | None = ma_cross_signal(
            closes,
            fast_len=self._cfg.fast_len,
            slow_len=self._cfg.slow_len,
        )
        if sig is None:
            logger.info(
                "MA_CROSS warmup",
                extra={
                    "symbol": self._symbol,
                    "tf": self._cfg.timeframe,
                    "need": max(self._cfg.fast_len, self._cfg.slow_len) + 2,
                    "have": len(closes),
                },
            )
            return

        logger.info(
            "MA_CROSS signal",
            extra={
                "symbol": self._symbol,
                "tf": self._cfg.timeframe,
                "side": sig.side,
                "fast": str(sig.fast),
                "slow": str(sig.slow),
                "prev_fast": str(sig.prev_fast),
                "prev_slow": str(sig.prev_slow),
            },
        )
