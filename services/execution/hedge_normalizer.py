from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .errors import ExchangeParamValidationError
from .models import NormalizedOrderRequest, PositionMode, PositionSide, validate_order_request


@dataclass(frozen=True, slots=True)
class NormalizedCcxtOrderCall:
    symbol: str
    type: str
    side: str
    amount: Any
    price: Any
    params: dict[str, Any]


class HedgeModeNormalizer:
    """Build ccxt create_order call with normalized hedge/dual-position semantics.

    This is the core place where exchange-specific hedge differences are normalized.
    """

    def __init__(self, *, exchange_id: str):
        self._exchange_id = exchange_id

    def build_create_order(self, req: NormalizedOrderRequest) -> NormalizedCcxtOrderCall:
        validate_order_request(req)

        params: dict[str, Any] = {}
        if req.extra:
            params.update(dict(req.extra))

        # reduceOnly is common, but support differs by exchange; we set it as best-effort.
        if req.reduce_only:
            params.setdefault("reduceOnly", True)

        if req.position_mode == "hedge":
            self._apply_hedge_params(params, req.position_side)
        else:
            # one_way: do not set hedge-specific fields.
            pass

        return NormalizedCcxtOrderCall(
            symbol=req.symbol,
            type=req.type,
            side=req.side,
            amount=req.amount,
            price=req.price,
            params=params,
        )

    def _apply_hedge_params(self, params: dict[str, Any], position_side: PositionSide | None) -> None:
        if position_side not in ("LONG", "SHORT"):
            raise ExchangeParamValidationError("hedge requires position_side LONG|SHORT")

        ex = self._exchange_id

        # Exchange-specific hedge params normalization.
        if ex == "binance":
            # Binance USDT-M futures hedge mode:
            # order param: positionSide = LONG|SHORT
            params.setdefault("positionSide", position_side)
            return

        if ex == "bybit":
            # Bybit (Linear USDT swap) hedge mode:
            # - positionIdx required (1=long, 2=short)
            # - reduceOnly is supported via params["reduceOnly"]=True (set above).
            params.setdefault("positionIdx", 1 if position_side == "LONG" else 2)
            return

        if ex == "okx":
            # OKX: posSide = long|short
            params.setdefault("posSide", "long" if position_side == "LONG" else "short")
            return

        if ex == "bingx":
            # BingX: positionSide is required for hedge.
            params.setdefault("positionSide", position_side)
            return

        if ex == "mexc":
            # MEXC: positionSide required.
            params.setdefault("positionSide", position_side)
            return

        if ex in ("kucoinfutures", "gateio", "htx"):
            # These are supported later with dedicated adapters (API differs, may require pre-checks).
            # For now we keep explicit error to avoid silent wrong trading.
            raise ExchangeParamValidationError(f"hedge normalization not implemented for exchange={ex}")

        raise ExchangeParamValidationError(f"unknown exchange for hedge normalization: {ex}")


@dataclass(frozen=True, slots=True)
class PositionModeState:
    mode: PositionMode
    # Add exchange-specific raw flags if needed later (e.g. binance dualSidePosition bool)
    raw: Mapping[str, Any] | None = None
