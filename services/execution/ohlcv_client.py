from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ohlcv import Candle, candles_from_ccxt_ohlcv
from .transport_ccxt import CcxtAsyncTransport


@dataclass(frozen=True, slots=True)
class OhlcvRequest:
    symbol: str
    timeframe: str
    limit: int
    since_ms: Optional[int] = None


class OhlcvRestClient:
    def __init__(self, *, transport: CcxtAsyncTransport):
        self._transport = transport

    async def fetch_history(self, req: OhlcvRequest) -> list[Candle]:
        rows = await self._transport.fetch_ohlcv(
            symbol=req.symbol,
            timeframe=req.timeframe,
            since=req.since_ms,
            limit=req.limit,
            params={},
        )
        return candles_from_ccxt_ohlcv(symbol=req.symbol, timeframe=req.timeframe, ohlcv_rows=rows)

    async def fetch_latest(self, *, symbol: str, timeframe: str) -> Candle:
        # We fetch 2 to safely handle exchanges that may return the previous bar as well.
        rows = await self._transport.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=None, limit=2, params={})
        candles = candles_from_ccxt_ohlcv(symbol=symbol, timeframe=timeframe, ohlcv_rows=rows)
        return candles[-1]
