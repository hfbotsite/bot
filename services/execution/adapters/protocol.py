from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol

from services.execution.intent_registry import OrderIntentRegistry
from services.execution.models import (
    ExchangeId,
    NormalizedFill,
    NormalizedOrder,
    NormalizedOrderRequest,
    NormalizedPosition,
    PositionMode,
)
from services.execution.transport_ccxt import TransportConfig
from services.execution.hedge_normalizer import NormalizedCcxtOrderCall


class ExchangeAdapter(Protocol):
    exchange_id: ExchangeId

    def ccxt_options(self, cfg: TransportConfig) -> dict[str, Any]:
        """Return exchange-specific ccxt constructor options.

        Notes:
        - Must NOT include apiKey/secret/password, timeout, enableRateLimit, defaultType.
          Those are applied by the Transport.
        - May include nested 'options' dict and other exchange-specific flags.
        """
        ...

    def build_create_order(self, req: NormalizedOrderRequest) -> NormalizedCcxtOrderCall:
        """Build ccxt create_order call for the exchange (symbol + params)."""
        ...

    def normalize_create_order_call(
        self, call: NormalizedCcxtOrderCall, *, market: Mapping[str, Any]
    ) -> NormalizedCcxtOrderCall:
        """Apply precision/min limits normalization for this exchange (may be exchange-specific)."""
        ...

    def map_order(self, raw: Mapping[str, Any], *, fallback: Optional[NormalizedOrderRequest]) -> NormalizedOrder:
        ...

    def map_trade(self, raw: Mapping[str, Any], *, intents: OrderIntentRegistry) -> NormalizedFill:
        ...

    def map_positions(self, raw: list[Mapping[str, Any]], *, position_mode: PositionMode) -> list[NormalizedPosition]:
        ...
