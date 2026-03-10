from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional


@dataclass(frozen=True, slots=True)
class MarketRules:
    """Normalized market constraints/precision for order creation.

    Values come from ccxt market() output after load_markets().

    Notes:
    - price_precision/amount_precision are decimal places (0..N) as used by ccxt for precision rounding.
    - min_amount/min_cost are best-effort (some exchanges may omit).
    - contract_size is populated for contract markets when available.
    """

    symbol: str
    price_precision: int | None
    amount_precision: int | None

    min_amount: Decimal | None
    min_cost: Decimal | None
    contract_size: Decimal | None

    @staticmethod
    def from_ccxt_market(*, market: Mapping[str, Any]) -> "MarketRules":
        symbol = str(market.get("symbol") or "")

        prec = market.get("precision") or {}
        price_prec = prec.get("price")
        amount_prec = prec.get("amount")

        limits = market.get("limits") or {}
        lim_amount = (limits.get("amount") or {}).get("min")
        lim_cost = (limits.get("cost") or {}).get("min")

        # ccxt uses different keys; keep best-effort.
        contract_size = market.get("contractSize") or market.get("contract_size")

        return MarketRules(
            symbol=symbol,
            price_precision=int(price_prec) if price_prec is not None else None,
            amount_precision=int(amount_prec) if amount_prec is not None else None,
            min_amount=Decimal(str(lim_amount)) if lim_amount is not None else None,
            min_cost=Decimal(str(lim_cost)) if lim_cost is not None else None,
            contract_size=Decimal(str(contract_size)) if contract_size is not None else None,
        )


def _quantize_floor(*, x: Decimal, decimals: int) -> Decimal:
    q = Decimal("1").scaleb(-decimals)  # 10^-decimals
    return (x // q) * q


def round_price(*, price: Decimal, price_precision: Optional[int]) -> Decimal:
    if price_precision is None:
        return price
    if price_precision < 0:
        return price
    return _quantize_floor(x=price, decimals=price_precision)


def round_amount(*, amount: Decimal, amount_precision: Optional[int]) -> Decimal:
    if amount_precision is None:
        return amount
    if amount_precision < 0:
        return amount
    return _quantize_floor(x=amount, decimals=amount_precision)


def validate_min_limits(
    *,
    amount: Decimal,
    price: Optional[Decimal],
    min_amount: Optional[Decimal],
    min_cost: Optional[Decimal],
) -> bool:
    if min_amount is not None and amount < min_amount:
        return False
    if min_cost is not None and price is not None:
        if amount * price < min_cost:
            return False
    return True
