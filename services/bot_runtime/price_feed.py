from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from services.execution.ohlcv import Candle

from .candle_store import CandleStore


@dataclass(frozen=True, slots=True)
class PriceTick:
    symbol: str
    ts: datetime
    price: Decimal


@dataclass(frozen=True, slots=True)
class PriceStatus:
    ok: bool
    reason: str
    tick: PriceTick | None
    last_update_ms: int | None


class PriceFeed:
    """Provides latest usable price from candles.

    Current policy:
    - Use 1m candle close as the 'price'.
    - Consider data stale if last update is older than `stale_after_seconds`.
    """

    def __init__(self, *, store: CandleStore, stale_after_seconds: int) -> None:
        self._store = store
        self._stale_after_seconds = int(stale_after_seconds)

    def status(self, *, symbol: str) -> PriceStatus:
        candle: Candle | None = self._store.latest(symbol=symbol, timeframe="1m")
        if candle is None:
            return PriceStatus(ok=False, reason="no_candle", tick=None, last_update_ms=None)

        last_update_ms = self._store.last_update_ms(symbol=symbol, timeframe="1m")
        if last_update_ms is None:
            return PriceStatus(ok=False, reason="no_last_update", tick=None, last_update_ms=None)

        now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        age_ms = now_ms - last_update_ms
        if age_ms > (self._stale_after_seconds * 1000):
            return PriceStatus(ok=False, reason=f"stale:{age_ms}ms", tick=None, last_update_ms=last_update_ms)

        tick = PriceTick(
            symbol=symbol,
            ts=datetime.now(tz=timezone.utc),
            price=candle.close,
        )
        return PriceStatus(ok=True, reason="ok", tick=tick, last_update_ms=last_update_ms)

    def latest_price(self, *, symbol: str) -> PriceTick | None:
        st = self.status(symbol=symbol)
        return st.tick
