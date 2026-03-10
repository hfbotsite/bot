from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Iterable, Optional

import websockets

from services.execution.ohlcv import Candle


logger = logging.getLogger("bot_runtime.candles_ws")


@dataclass(frozen=True, slots=True)
class CandleEvent:
    candle: Candle
    kind: str  # "snapshot" | "update"


@dataclass(frozen=True, slots=True)
class WsCandlesClient:
    url: str
    exchange: str
    symbol: str


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


def _parse_candle_row(*, symbol: str, timeframe: str, row: list[Any]) -> Candle:
    # Expected format: [timestamp_ms, open, high, low, close, volume]
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        open_time_ms=int(row[0]),
        open=_d(row[1]),
        high=_d(row[2]),
        low=_d(row[3]),
        close=_d(row[4]),
        volume=_d(row[5]),
    )


class WsCandlesStream:
    """Consumes the external candles WS and yields normalized CandleEvent.

    Assumptions from the agreed contract:
    - After subscribe, WS replays/sends >=300 candles (snapshot/replay).
    - Then it sends live candle updates as op=update.
    """

    def __init__(self, *, client: WsCandlesClient):
        self._client = client

    async def stream_timeframe(self, *, timeframe: str) -> AsyncIterator[CandleEvent]:
        while True:
            try:
                async with websockets.connect(self._client.url, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(
                        json.dumps(
                            {
                                "op": "subscribe",
                                "exchange": self._client.exchange,
                                "pair": self._client.symbol,
                                "timeframe": timeframe,
                            }
                        )
                    )

                    async for msg in ws:
                        data = json.loads(msg)

                        op = data.get("op")
                        if op == "update":
                            candle = _parse_candle_row(
                                symbol=self._client.symbol,
                                timeframe=timeframe,
                                row=data["d"],
                            )
                            yield CandleEvent(candle=candle, kind="update")
                            continue

                        if op == "snapshot":
                            # Optional protocol: snapshot returns {"d": [[...],[...],...]}
                            for row in data.get("d") or []:
                                candle = _parse_candle_row(
                                    symbol=self._client.symbol,
                                    timeframe=timeframe,
                                    row=row,
                                )
                                yield CandleEvent(candle=candle, kind="snapshot")
                            continue

                        # Unknown messages are ignored but logged.
                        logger.debug("WS unknown message", extra={"data": data})
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(
                    "WS timeframe stream error; reconnecting",
                    extra={
                        "timeframe": timeframe,
                        "err": str(e),
                        "err_type": type(e).__name__,
                    },
                )
                await asyncio.sleep(2)
