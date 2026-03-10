from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .errors import ExchangeParamValidationError
from .intent_registry import OrderIntentRegistry
from .models import (
    NormalizedFill,
    NormalizedOrder,
    NormalizedOrderRequest,
    NormalizedPosition,
    PositionMode,
)
from .market_rules import MarketRules
from .transport_ccxt import CcxtAsyncTransport
from .adapters.base import BaseCcxtAdapter


@dataclass(slots=True)
class ExecutionClientConfig:
    position_mode: PositionMode = "hedge"


class ExecutionClient:
    """High-level execution client (normalized) delegating exchange-specific logic to adapter.

    - adapter builds exchange-specific order params and performs symbol mapping
    - adapter maps raw ccxt results to NormalizedOrder/Fill/Position
    - client keeps OrderIntentRegistry for later fill attribution
    - client normalizes order amounts/prices to market precision and validates min limits (best-effort)
    """

    def __init__(
        self,
        *,
        cfg: ExecutionClientConfig,
        adapter: BaseCcxtAdapter,
        transport: CcxtAsyncTransport,
        intents: OrderIntentRegistry,
    ):
        self._cfg = cfg
        self._adapter = adapter
        self._transport = transport
        self._intents = intents

    async def create_order(self, req: NormalizedOrderRequest) -> NormalizedOrder:
        call = self._adapter.build_create_order(req)

        # --- Market precision / limits normalization (adapter-level) ---
        try:
            mkt = self._transport.market(call.symbol)
            call = self._adapter.normalize_create_order_call(call, market=mkt)
        except ExchangeParamValidationError:
            raise
        except Exception:  # noqa: BLE001
            pass

        if req.client_order_id:
            exit_reason = None
            if req.reduce_only:
                coid = str(req.client_order_id).lower()
                if "-squeeze-" in coid:
                    exit_reason = "squeeze_exit"
                elif "-sl-" in coid:
                    exit_reason = "stop_loss_exit"
                elif "-tp-" in coid:
                    exit_reason = "tp_market_exit"
                elif "-exit-ind-" in coid:
                    exit_reason = "indicators_exit"

            self._intents.put(
                client_order_id=req.client_order_id,
                position_side=req.position_side,
                reduce_only=req.reduce_only,
                exit_reason=exit_reason,
            )
            call.params.setdefault("clientOrderId", req.client_order_id)

        raw = await self._transport.create_order(
            symbol=call.symbol,
            type=call.type,
            side=call.side,
            amount=call.amount,
            price=call.price,
            params=call.params,
        )
        return self._adapter.map_order(raw, fallback=req)

    async def cancel_order(
        self,
        *,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> NormalizedOrder:
        if order_id is None and client_order_id is None:
            raise ExchangeParamValidationError("cancel requires order_id or client_order_id")

        params: dict[str, object] = {}
        if client_order_id is not None:
            params["clientOrderId"] = client_order_id

        raw = await self._transport.cancel_order(order_id=order_id or client_order_id, symbol=symbol, params=params)
        return self._adapter.map_order(raw, fallback=None)

    async def fetch_my_trades(
        self, *, symbol: Optional[str] = None, since_ms: Optional[int] = None, limit: Optional[int] = None
    ) -> list[NormalizedFill]:
        raw_trades = await self._transport.fetch_my_trades(symbol=symbol, since=since_ms, limit=limit, params={})
        return [self._adapter.map_trade(t, intents=self._intents) for t in raw_trades]

    async def fetch_positions(self, *, symbols: Optional[list[str]] = None) -> list[NormalizedPosition]:
        raw_positions = await self._transport.fetch_positions(symbols=symbols, params={})
        return self._adapter.map_positions(raw_positions, position_mode=self._cfg.position_mode)
