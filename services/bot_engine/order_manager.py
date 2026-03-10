from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from services.execution.exchange_client import ExecutionClient
from services.execution.models import NormalizedOrder, NormalizedOrderRequest

from .orders_repo import OrdersRepo, UpsertOrder

logger = logging.getLogger("bot_engine.order_manager")


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    created: int
    canceled: int


class OrderManager:
    """Reconcile desired orders with exchange open orders.

    MVP rules:
      - We manage only orders created by bot (identified by client_order_id prefixing scheme).
      - We do not mirror foreign/manual orders.
      - For each desired order, if an open order exists with same client_order_id => keep.
      - If an open order exists but is not desired => cancel (only if it has our client_order_id prefix).
      - For desired orders missing on exchange => create.
    """

    def __init__(
        self,
        *,
        bot_id: str,
        bot_run_id: str,
        client: ExecutionClient,
        orders_repo: OrdersRepo,
    ):
        self._bot_id = bot_id
        self._bot_run_id = bot_run_id
        self._client = client
        self._orders_repo = orders_repo

    @property
    def _coid_prefix(self) -> str:
        # All bot orders should include this prefix to make filtering safe.
        return f"{self._bot_id}-"

    def _is_ours(self, client_order_id: str | None) -> bool:
        return bool(client_order_id) and client_order_id.startswith(self._coid_prefix)

    async def reconcile(
        self,
        *,
        symbol: str,
        desired: Sequence[NormalizedOrderRequest],
        open_orders_raw: Sequence[Mapping[str, Any]],
    ) -> ReconcileResult:
        desired_by_coid: dict[str, NormalizedOrderRequest] = {
            d.client_order_id: d for d in desired if d.client_order_id
        }

        open_by_coid: dict[str, Mapping[str, Any]] = {}
        for o in open_orders_raw:
            coid = o.get("clientOrderId") or (o.get("info") or {}).get("orderLinkId")
            if isinstance(coid, str) and coid:
                open_by_coid[coid] = o

        # Cancel orders that are ours but not desired.
        canceled = 0
        for coid, raw in open_by_coid.items():
            if not self._is_ours(coid):
                continue
            if coid in desired_by_coid:
                continue
            ex_order_id = raw.get("id") if isinstance(raw, dict) else None
            try:
                await self._client.cancel_order(
                    order_id=str(ex_order_id) if ex_order_id else None,
                    client_order_id=coid,
                    symbol=symbol,
                )
                canceled += 1
            except Exception:
                logger.exception("Failed to cancel order", extra={"client_order_id": coid, "symbol": symbol})

        created = 0
        for coid, req in desired_by_coid.items():
            if coid in open_by_coid:
                continue
            try:
                norm: NormalizedOrder = await self._client.create_order(req)
                created += 1
                self._orders_repo.upsert(
                    UpsertOrder(
                        bot_run_id=self._bot_run_id,
                        exchange=norm.exchange,
                        symbol=norm.symbol,
                        exchange_order_id=norm.exchange_order_id,
                        client_order_id=norm.client_order_id,
                        type=norm.type,
                        side=norm.side,
                        position_mode=norm.position_mode,
                        position_side=norm.position_side,
                        reduce_only=norm.reduce_only,
                        price=norm.price,
                        amount=norm.amount,
                        filled=norm.filled,
                        status=norm.status,
                        ts=norm.ts,
                    )
                )
            except Exception:
                logger.exception("Failed to create desired order", extra={"client_order_id": coid, "symbol": symbol})

        return ReconcileResult(created=created, canceled=canceled)
