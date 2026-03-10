from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from services.execution.ohlcv import Candle

from .candles_ws import CandleEvent


_TF_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "1d": 86400,
}


class MockCandlesStream:
    """Offline candles generator to develop bot runtime without external WS.

    Design goals:
    - Deterministic enough to reproduce behavior via seed (optional).
    - Generates a plausible random-walk close series.
    - Emits candles aligned to timeframe boundaries in "simulated time",
      but accelerated by `speedup`.
    """

    def __init__(
        self,
        *,
        symbol: str,
        start_price: Decimal = Decimal("100.0"),
        seed: int | None = None,
        speedup: float = 60.0,
    ) -> None:
        self._symbol = symbol
        self._price = start_price
        self._rng = random.Random(seed)
        self._speedup = float(speedup)

    def _tf_seconds(self, timeframe: str) -> int:
        if timeframe not in _TF_SECONDS:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return _TF_SECONDS[timeframe]

    def bootstrap(self, *, timeframe: str, bars: int) -> list[CandleEvent]:
        tf_sec = self._tf_seconds(timeframe)
        tf_ms = tf_sec * 1000

        now = datetime.now(tz=timezone.utc)
        now_ms = int(now.timestamp() * 1000)
        base_ms = now_ms - (now_ms % tf_ms)

        out: list[CandleEvent] = []
        # generate history ending "now" (bars back)
        start_i = -max(0, int(bars))
        for i in range(start_i, 0):
            drift = Decimal(str(self._rng.uniform(-0.002, 0.002)))
            close = (self._price * (Decimal("1.0") + drift)).quantize(Decimal("0.01"))
            high = max(self._price, close) * Decimal("1.001")
            low = min(self._price, close) * Decimal("0.999")
            open_ = self._price
            volume = Decimal(str(self._rng.uniform(10, 1000))).quantize(Decimal("0.0001"))

            ts_ms = base_ms + i * tf_ms
            candle = Candle(
                symbol=self._symbol,
                timeframe=timeframe,
                open_time_ms=ts_ms,
                open=open_.quantize(Decimal("0.01")),
                high=high.quantize(Decimal("0.01")),
                low=low.quantize(Decimal("0.01")),
                close=close,
                volume=volume,
            )
            self._price = close
            out.append(CandleEvent(candle=candle, kind="snapshot"))

        return out

    async def stream_timeframe(self, *, timeframe: str):
        tf_sec = self._tf_seconds(timeframe)
        tf_ms = tf_sec * 1000

        # "Simulated now" aligned to timeframe boundary
        now = datetime.now(tz=timezone.utc)
        now_ms = int(now.timestamp() * 1000)
        base_ms = now_ms - (now_ms % tf_ms)

        i = 0
        while True:
            # price random walk
            drift = Decimal(str(self._rng.uniform(-0.002, 0.002)))  # +/-0.2%
            close = (self._price * (Decimal("1.0") + drift)).quantize(Decimal("0.01"))
            high = max(self._price, close) * Decimal("1.001")
            low = min(self._price, close) * Decimal("0.999")
            open_ = self._price
            volume = Decimal(str(self._rng.uniform(10, 1000))).quantize(Decimal("0.0001"))

            ts_ms = base_ms + i * tf_ms
            candle = Candle(
                symbol=self._symbol,
                timeframe=timeframe,
                open_time_ms=ts_ms,
                open=open_.quantize(Decimal("0.01")),
                high=high.quantize(Decimal("0.01")),
                low=low.quantize(Decimal("0.01")),
                close=close,
                volume=volume,
            )

            self._price = close
            i += 1

            yield CandleEvent(candle=candle, kind="update")

            # Accelerated sleep: one candle per (tf_sec / speedup) real seconds
            await asyncio.sleep(max(0.001, tf_sec / self._speedup))
