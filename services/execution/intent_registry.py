from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .models import PositionSide


@dataclass(frozen=True, slots=True)
class OrderIntent:
    client_order_id: str
    position_side: Optional[PositionSide]
    reduce_only: bool
    created_ts: float
    exit_reason: Optional[str] = None


class OrderIntentRegistry:
    """In-memory registry to attribute fills/trades to position_side.

    Some exchanges don't reliably include posSide/positionIdx in trade history.
    We store our intent by client_order_id for later reconciliation.

    NOTE: For containerized bots, in-memory is acceptable for MVP. Later we can persist.
    """

    def __init__(self, *, ttl_seconds: int = 6 * 60 * 60):
        self._ttl = ttl_seconds
        self._by_client_id: dict[str, OrderIntent] = {}

    def put(
        self,
        *,
        client_order_id: str,
        position_side: Optional[PositionSide],
        reduce_only: bool,
        exit_reason: Optional[str] = None,
    ) -> None:
        self._by_client_id[client_order_id] = OrderIntent(
            client_order_id=client_order_id,
            position_side=position_side,
            reduce_only=reduce_only,
            created_ts=time.time(),
            exit_reason=exit_reason,
        )

    def get(self, client_order_id: str) -> Optional[OrderIntent]:
        self._gc()
        return self._by_client_id.get(client_order_id)

    def _gc(self) -> None:
        now = time.time()
        expired = [k for k, v in self._by_client_id.items() if now - v.created_ts > self._ttl]
        for k in expired:
            self._by_client_id.pop(k, None)
