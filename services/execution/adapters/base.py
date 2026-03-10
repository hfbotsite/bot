from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional

from services.execution.errors import ExchangeParamValidationError
from services.execution.hedge_normalizer import NormalizedCcxtOrderCall
from services.execution.intent_registry import OrderIntentRegistry
from services.execution.market_rules import MarketRules, round_amount, round_price, validate_min_limits
from services.execution.models import (
    ExchangeId,
    NormalizedFill,
    NormalizedOrder,
    NormalizedOrderRequest,
    NormalizedPosition,
    PositionMode,
    PositionSide,
)
from services.execution.symbols import resolve_ccxt_symbol
from services.execution.transport_ccxt import TransportConfig


def _d(x: Any) -> Optional[Decimal]:
    if x is None:
        return None
    try:
        return Decimal(str(x))
    except Exception:  # noqa: BLE001
        return None


def _ts_ms_to_dt(ts_ms: Any) -> Optional[datetime]:
    if ts_ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


@dataclass(frozen=True, slots=True)
class SymbolContext:
    """What kind of instrument we trade.

    For MVP we only support swaps/perps (no spot).
    """

    market: str = "swap"


class BaseCcxtAdapter:
    """Default adapter that keeps existing MVP behavior.

    - Encapsulates exchange-specific order params (hedge mode)
    - Encapsulates mapping of raw ccxt payloads to Normalized* models (best-effort)
    - Encapsulates canonical(BASE/QUOTE) -> ccxt_symbol resolution using loaded markets
    """

    def __init__(self, *, exchange_id: ExchangeId, symbol_ctx: SymbolContext | None = None):
        self.exchange_id = exchange_id
        self._symbol_ctx = symbol_ctx or SymbolContext()

        self._markets: Mapping[str, Any] | None = None
        self._base_coin: str | None = None
        self._quote_coin: str | None = None

    # ----- binding (runtime provides markets + base/quote from settings) -----

    def bind_markets(self, *, markets: Mapping[str, Any]) -> None:
        self._markets = markets

    def bind_symbol(self, *, base: str, quote: str) -> None:
        self._base_coin = base
        self._quote_coin = quote

    # ----- ccxt init options -----

    def ccxt_options(self, cfg: TransportConfig) -> dict[str, Any]:
        return {}

    # ----- symbols -----

    def to_ccxt_symbol(self, *, canonical_symbol: str) -> str:
        """Convert canonical BASE/QUOTE to ccxt symbol using loaded markets (best-effort)."""
        if self._markets is None:
            return canonical_symbol

        if self._base_coin and self._quote_coin:
            base = self._base_coin
            quote = self._quote_coin
        else:
            # fallback parse from "BASE/QUOTE"
            if "/" in canonical_symbol:
                base, quote = canonical_symbol.split("/", 1)
            else:
                return canonical_symbol

        res = resolve_ccxt_symbol(markets=self._markets, base=base, quote=quote, market=self._symbol_ctx.market)
        return res.ccxt_symbol

    # ----- order params (hedge/one-way) -----

    def build_create_order(self, req: NormalizedOrderRequest) -> NormalizedCcxtOrderCall:
        if req.exchange != self.exchange_id:
            raise ExchangeParamValidationError(
                f"Request exchange mismatch: req.exchange={req.exchange} adapter.exchange_id={self.exchange_id}"
            )

        params: dict[str, Any] = {}
        if req.extra:
            params.update(dict(req.extra))

        if req.reduce_only:
            params.setdefault("reduceOnly", True)

        if req.position_mode == "hedge":
            self._apply_hedge_params(params, req.position_side)

        symbol = self.to_ccxt_symbol(canonical_symbol=req.symbol)

        return NormalizedCcxtOrderCall(
            symbol=symbol,
            type=req.type,
            side=req.side,
            amount=req.amount,
            price=req.price,
            params=params,
        )

    def _apply_hedge_params(self, params: dict[str, Any], position_side: PositionSide | None) -> None:
        if position_side not in ("LONG", "SHORT"):
            raise ExchangeParamValidationError("hedge requires position_side LONG|SHORT")

        ex = self.exchange_id

        # Exchange-specific hedge params normalization.
        if ex == "binance":
            params.setdefault("positionSide", position_side)
            return

        if ex == "bybit":
            params.setdefault("positionIdx", 1 if position_side == "LONG" else 2)
            return

        if ex == "okx":
            params.setdefault("posSide", "long" if position_side == "LONG" else "short")
            return

        if ex == "bingx":
            params.setdefault("positionSide", position_side)
            return

        if ex == "mexc":
            params.setdefault("positionSide", position_side)
            return

        if ex in ("kucoinfutures", "gateio", "htx"):
            raise ExchangeParamValidationError(f"hedge normalization not implemented for exchange={ex}")

        raise ExchangeParamValidationError(f"unknown exchange for hedge normalization: {ex}")

    # ----- mapping: ccxt -> normalized -----

    def map_order(self, raw: Mapping[str, Any], *, fallback: Optional[NormalizedOrderRequest]) -> NormalizedOrder:
        exchange_order_id = raw.get("id") if isinstance(raw, dict) else None
        client_order_id = raw.get("clientOrderId") if isinstance(raw, dict) else None

        status = raw.get("status") if isinstance(raw, dict) else None
        status_map = {
            "open": "open",
            "closed": "filled",
            "canceled": "canceled",
            "rejected": "rejected",
        }
        norm_status = status_map.get(status, "created")

        typ = raw.get("type") if isinstance(raw, dict) else None
        side = raw.get("side") if isinstance(raw, dict) else None

        price = _d(raw.get("price") if isinstance(raw, dict) else None)
        amount = _d(raw.get("amount") if isinstance(raw, dict) else None)
        filled = _d(raw.get("filled") if isinstance(raw, dict) else None)
        avg_price = _d(raw.get("average") if isinstance(raw, dict) else None)
        ts = _ts_ms_to_dt(raw.get("timestamp") if isinstance(raw, dict) else None)

        position_mode = fallback.position_mode if fallback else None
        position_side = fallback.position_side if fallback else None
        reduce_only = fallback.reduce_only if fallback else None

        # Note: symbol may be ccxt-format; keep as-is in NormalizedOrder for now.
        # (If we need canonical symbols everywhere, adapter should map it back.)
        symbol = raw.get("symbol") if isinstance(raw, dict) else None
        if not symbol and fallback:
            symbol = fallback.symbol

        return NormalizedOrder(
            exchange=self.exchange_id,  # type: ignore[arg-type]
            symbol=str(symbol or ""),
            exchange_order_id=exchange_order_id,
            client_order_id=client_order_id,
            status=norm_status,  # type: ignore[arg-type]
            type=typ or "unknown",  # type: ignore[arg-type]
            side=side or "buy",  # type: ignore[arg-type]
            position_mode=position_mode,
            position_side=position_side,
            reduce_only=reduce_only,
            price=price,
            amount=amount,
            filled=filled,
            avg_price=avg_price,
            ts=ts,
            raw=raw,
        )

    def map_trade(self, raw: Mapping[str, Any], *, intents: OrderIntentRegistry) -> NormalizedFill:
        trade_id = str(raw.get("id") or "")
        order_id = raw.get("order")
        client_order_id = raw.get("clientOrderId")

        side = raw.get("side")

        position_side: Optional[PositionSide] = None
        raw_info = raw.get("info") if isinstance(raw, dict) else None
        if isinstance(raw_info, dict):
            ps = raw_info.get("positionSide") or raw_info.get("posSide")
            if isinstance(ps, str):
                psu = ps.upper()
                if psu in ("LONG", "SHORT"):
                    position_side = psu  # type: ignore[assignment]

        exit_reason: Optional[str] = None
        if position_side is None and client_order_id:
            intent = intents.get(str(client_order_id))
            if intent:
                position_side = intent.position_side
                exit_reason = intent.exit_reason

        ts = _ts_ms_to_dt(raw.get("timestamp")) or datetime.now(tz=timezone.utc)

        fee = raw.get("fee") if isinstance(raw, dict) else None
        fee_cost = None
        fee_currency = None
        if isinstance(fee, dict):
            fee_cost = _d(fee.get("cost"))
            fee_currency = fee.get("currency")

        taker_or_maker = raw.get("takerOrMaker")
        is_maker = True if taker_or_maker == "maker" else (False if taker_or_maker == "taker" else None)

        quote_qty = _d(raw.get("cost"))

        symbol = str(raw.get("symbol") or "")

        return NormalizedFill(
            event_id=f"{self.exchange_id}:{trade_id}",
            ts=ts,
            exchange=self.exchange_id,  # type: ignore[arg-type]
            symbol=symbol,
            exchange_trade_id=trade_id,
            exchange_order_id=str(order_id) if order_id is not None else None,
            client_order_id=str(client_order_id) if client_order_id is not None else None,
            side=str(side or "buy"),  # type: ignore[arg-type]
            position_side=position_side,
            price=_d(raw.get("price")) or Decimal("0"),
            qty=_d(raw.get("amount")) or Decimal("0"),
            quote_qty=quote_qty,
            fee_cost=fee_cost,
            fee_currency=str(fee_currency) if fee_currency else None,
            is_maker=is_maker,
            margin_mode=None,
            leverage=None,
            collateral_asset=None,
            raw={**raw, "_exit_reason": exit_reason} if exit_reason is not None else raw,
        )

    def map_positions(self, raw: list[Mapping[str, Any]], *, position_mode: PositionMode) -> list[NormalizedPosition]:
        out: list[NormalizedPosition] = []
        for p in raw:
            pos = self._map_position(p, position_mode=position_mode)
            if pos:
                out.append(pos)
        return out

    def _map_position(self, p: Mapping[str, Any], *, position_mode: PositionMode) -> Optional[NormalizedPosition]:
        symbol = p.get("symbol")
        if not symbol:
            return None

        contracts = p.get("contracts") or p.get("contractSize") or p.get("positionAmt") or p.get("size")
        qty = _d(contracts) or Decimal("0")

        position_side: PositionSide = "ONE_WAY"
        info = p.get("info") if isinstance(p, dict) else None
        if isinstance(info, dict):
            ps = info.get("positionSide") or info.get("posSide")
            if isinstance(ps, str):
                psu = ps.upper()
                if psu in ("LONG", "SHORT"):
                    position_side = psu  # type: ignore[assignment]

        avg_entry = _d(p.get("entryPrice") or p.get("avgEntryPrice") or p.get("avgPrice"))
        mark = _d(p.get("markPrice"))
        liq = _d(p.get("liquidationPrice"))
        upl = _d(p.get("unrealizedPnl") or p.get("unrealizedProfit"))

        return NormalizedPosition(
            exchange=self.exchange_id,  # type: ignore[arg-type]
            symbol=str(symbol),
            position_mode=position_mode,
            position_side=position_side,
            qty=qty,
            avg_entry_price=avg_entry,
            mark_price=mark,
            liquidation_price=liq,
            unrealized_pnl=upl,
            leverage=None,
            margin_mode=None,
            collateral_asset=None,
            raw=p,
        )

    # ----- optional helpers for market rules -----

    def normalize_create_order_call(self, call: NormalizedCcxtOrderCall, *, market: Mapping[str, Any]) -> NormalizedCcxtOrderCall:
        """Normalize price/amount to precision and validate min limits (best-effort).

        This is adapter responsibility to allow exchange-specific overrides later
        (tickSize/stepSize, contractSize math, etc).
        """
        try:
            rules = MarketRules.from_ccxt_market(market=market)
        except Exception:  # noqa: BLE001
            return call

        # Amount: mandatory
        try:
            amt = Decimal(str(call.amount))
            amt = round_amount(amount=amt, amount_precision=rules.amount_precision)
            call.amount = amt  # type: ignore[assignment]
        except Exception:  # noqa: BLE001
            pass

        # Price: for limit orders
        if call.price is not None:
            try:
                px = Decimal(str(call.price))
                px = round_price(price=px, price_precision=rules.price_precision)
                call.price = px  # type: ignore[assignment]
            except Exception:  # noqa: BLE001
                pass

        try:
            amt2 = Decimal(str(call.amount))
            px2 = Decimal(str(call.price)) if call.price is not None else None
            if not validate_min_limits(amount=amt2, price=px2, min_amount=rules.min_amount, min_cost=rules.min_cost):
                raise ExchangeParamValidationError(
                    f"Order below min limits for {rules.symbol}: amount={amt2}, price={px2}, "
                    f"min_amount={rules.min_amount}, min_cost={rules.min_cost}"
                )
        except ExchangeParamValidationError:
            raise
        except Exception:  # noqa: BLE001
            pass

        return call

    def market_rules_from_ccxt_market(self, market: Mapping[str, Any]) -> MarketRules:
        return MarketRules.from_ccxt_market(market=market)
