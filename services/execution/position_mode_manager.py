from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .errors import PositionModeMismatchError, TemporaryNetworkError
from .hedge_normalizer import PositionModeState
from .models import PositionMode
from .transport_ccxt import CcxtAsyncTransport


@dataclass(frozen=True, slots=True)
class PositionModePolicy:
    # REQUIRE: must be in hedge; try to set; if impossible => error
    # PREFER: try to set, but allow one_way
    # AS_IS: do not change, only detect
    name: str  # "REQUIRE" | "PREFER" | "AS_IS"


class PositionModeManager:
    """Detect/ensure hedge(one-way) position mode with caching.

    WARNING: Exchange APIs differ a lot. For MVP we implement BINANCE only.
    Others can be added via per-exchange strategy methods.

    In our architecture, if exchange doesn't support mode switching via ccxt,
    we can only 'detect' and fail if policy is REQUIRE.
    """

    def __init__(self, *, exchange_id: str, transport: CcxtAsyncTransport, cache_ttl_s: int = 60):
        self._exchange_id = exchange_id
        self._transport = transport
        self._cache_ttl_s = cache_ttl_s
        self._cached: tuple[float, PositionModeState] | None = None

    async def get_position_mode(self) -> PositionModeState:
        now = time.time()
        if self._cached and now - self._cached[0] < self._cache_ttl_s:
            return self._cached[1]

        state = await self._detect_position_mode()
        self._cached = (now, state)
        return state

    async def ensure(self, *, target: PositionMode, policy: PositionModePolicy) -> PositionModeState:
        cur = await self.get_position_mode()
        if cur.mode == target:
            return cur

        if policy.name == "AS_IS":
            return cur

        # attempt to set
        try:
            await self._set_position_mode(target)
        except Exception as e:  # noqa: BLE001
            # refresh current
            self._cached = None
            cur2 = await self.get_position_mode()
            if policy.name == "PREFER":
                return cur2
            raise PositionModeMismatchError(
                f"failed to set position mode {target}; current={cur2.mode}; exchange={self._exchange_id}"
            ) from e

        # verify
        self._cached = None
        after = await self.get_position_mode()
        if after.mode != target:
            if policy.name == "PREFER":
                return after
            raise PositionModeMismatchError(
                f"position mode mismatch after set: want={target} got={after.mode} exchange={self._exchange_id}"
            )
        return after

    async def _detect_position_mode(self) -> PositionModeState:
        ex = self._exchange_id

        # MVP: BINANCE only.
        if ex == "binance":
            # Binance futures: dualSidePosition indicates hedge mode.
            # ccxt provides raw endpoints via exchange.fapiPrivateGetPositionSideDual()
            # We intentionally call raw method on ccxt exchange instance.
            ccxt_ex = self._transport._exchange  # noqa: SLF001
            if ccxt_ex is None:
                raise RuntimeError("transport not open")

            try:
                raw = await ccxt_ex.fapiPrivateGetPositionSideDual()
            except Exception as e:  # noqa: BLE001
                raise TemporaryNetworkError(str(e)) from e

            dual = bool(raw.get("dualSidePosition"))
            return PositionModeState(mode=("hedge" if dual else "one_way"), raw=raw)

        # Unknown exchange: cannot detect reliably in MVP
        return PositionModeState(mode="one_way", raw={"warning": "mode detection not implemented"})

    async def _set_position_mode(self, target: PositionMode) -> None:
        ex = self._exchange_id

        if ex == "binance":
            ccxt_ex = self._transport._exchange  # noqa: SLF001
            if ccxt_ex is None:
                raise RuntimeError("transport not open")

            dual = "true" if target == "hedge" else "false"
            # Binance endpoint expects dualSidePosition=true|false (string in many examples)
            await ccxt_ex.fapiPrivatePostPositionSideDual({"dualSidePosition": dual})
            return

        raise PositionModeMismatchError(f"set position mode not implemented for exchange={ex}")
