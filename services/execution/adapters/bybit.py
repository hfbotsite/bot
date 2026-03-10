from __future__ import annotations

from typing import Any, Mapping

from services.execution.intent_registry import OrderIntentRegistry
from services.execution.models import NormalizedFill
from services.execution.transport_ccxt import TransportConfig

from .base import BaseCcxtAdapter


class BybitAdapter(BaseCcxtAdapter):
    def ccxt_options(self, cfg: TransportConfig) -> dict[str, Any]:
        # Bybit v5: some private endpoints (like fetch_currencies) may require "wallet/asset" permissions.
        # We don't need them for trading; disable to avoid auth errors during load_markets().
        return {"options": {"fetchCurrencies": False}}

    def map_trade(self, raw: Mapping[str, Any], *, intents: OrderIntentRegistry) -> NormalizedFill:
        # Bybit v5 execution payload uses "orderLinkId" as client order id.
        if isinstance(raw, dict) and not raw.get("clientOrderId"):
            info = raw.get("info")
            if isinstance(info, dict):
                oli = info.get("orderLinkId")
                if oli:
                    raw = {**raw, "clientOrderId": oli}

        return super().map_trade(raw, intents=intents)
