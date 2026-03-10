from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, Iterable, Optional, Tuple

from services.execution.ohlcv import Candle


@dataclass(frozen=True, slots=True)
class TimeframeState:
    timeframe: str
    maxlen: int
    required_bars: int


class CandleStore:
    """In-memory candles store per (symbol, timeframe) with upsert-by-ts semantics.

    - Keeps last `maxlen` candles in a deque.
    - Upserts by open_time_ms: if incoming candle has same ts as last -> replace.
    - If incoming candle has ts newer than last -> append.
    - Older candles are ignored (we assume ordered bootstrap/replay).
    """

    def __init__(self) -> None:
        self._buf: dict[tuple[str, str], Deque[Candle]] = {}
        self._last_update_ms: dict[tuple[str, str], int] = {}

    def ensure(self, *, symbol: str, tf_state: TimeframeState) -> None:
        key = (symbol, tf_state.timeframe)
        self._buf.setdefault(key, deque(maxlen=tf_state.maxlen))

    def upsert(self, candle: Candle) -> None:
        key = (candle.symbol, candle.timeframe)
        buf = self._buf.setdefault(key, deque(maxlen=350))

        if not buf:
            buf.append(candle)
            self._last_update_ms[key] = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
            return

        last = buf[-1]
        if candle.open_time_ms == last.open_time_ms:
            buf[-1] = candle
        elif candle.open_time_ms > last.open_time_ms:
            buf.append(candle)
        else:
            # Old out-of-order candle; ignore for now.
            return

        self._last_update_ms[key] = int(datetime.now(tz=timezone.utc).timestamp() * 1000)

    def count(self, *, symbol: str, timeframe: str) -> int:
        return len(self._buf.get((symbol, timeframe), ()))

    def is_warmed_up(self, *, symbol: str, tf_state: TimeframeState) -> bool:
        return self.count(symbol=symbol, timeframe=tf_state.timeframe) >= tf_state.required_bars

    def latest(self, *, symbol: str, timeframe: str) -> Candle | None:
        buf = self._buf.get((symbol, timeframe))
        if not buf:
            return None
        return buf[-1]

    def last_update_ms(self, *, symbol: str, timeframe: str) -> int | None:
        return self._last_update_ms.get((symbol, timeframe))

    def snapshot(self, *, symbol: str, timeframe: str) -> list[Candle]:
        buf = self._buf.get((symbol, timeframe))
        return list(buf) if buf else []
