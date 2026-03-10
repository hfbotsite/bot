from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    timeframe: str

    open_time_ms: int

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def open_time_dt(self) -> datetime:
        return datetime.fromtimestamp(self.open_time_ms / 1000, tz=timezone.utc)


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


def candles_from_ccxt_ohlcv(
    *,
    symbol: str,
    timeframe: str,
    ohlcv_rows: Iterable[list[Any]],
) -> list[Candle]:
    out: list[Candle] = []
    for row in ohlcv_rows:
        # CCXT format: [timestamp, open, high, low, close, volume]
        ts = int(row[0])
        out.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time_ms=ts,
                open=_d(row[1]),
                high=_d(row[2]),
                low=_d(row[3]),
                close=_d(row[4]),
                volume=_d(row[5]),
            )
        )
    return out
