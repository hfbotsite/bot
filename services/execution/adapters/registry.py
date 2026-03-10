from __future__ import annotations

from services.execution.models import ExchangeId

from .base import BaseCcxtAdapter
from .bybit import BybitAdapter


def get_adapter(*, exchange_id: ExchangeId) -> BaseCcxtAdapter:
    # For now we return concrete BaseCcxtAdapter subclasses (runtime code also uses bind_* helpers).
    # If we later enforce a Protocol return type, we can adjust signature accordingly.
    if exchange_id == "bybit":
        return BybitAdapter(exchange_id=exchange_id)

    return BaseCcxtAdapter(exchange_id=exchange_id)
