from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SymbolBuildResult:
    base: str
    quote: str
    ccxt_symbol: str


def parse_base_coins(base_coin_value: str) -> list[str]:
    # Supports: "ETH" or "ETH,BTC" or "ETH, BTC, SOL"
    parts = [p.strip() for p in base_coin_value.split(",")]
    return [p for p in parts if p]


def build_symbol_candidates(*, base: str, quote: str, market: str) -> list[str]:
    base = base.strip().upper()
    quote = quote.strip().upper()

    # Spot-like
    candidates = [f"{base}/{quote}"]

    # Perpetual swaps in CCXT often use ":QUOTE" suffix for linear contracts.
    if market.lower() in ("futures", "swap", "perp", "perpetual"):
        candidates.insert(0, f"{base}/{quote}:{quote}")

    return candidates


def resolve_ccxt_symbol(*, markets: Any, base: str, quote: str, market: str) -> SymbolBuildResult:
    markets = markets or {}
    candidates = build_symbol_candidates(base=base, quote=quote, market=market)

    for s in candidates:
        if s in markets:
            return SymbolBuildResult(base=base, quote=quote, ccxt_symbol=s)

    # fallback to first candidate (will likely fail downstream with a clear error)
    return SymbolBuildResult(base=base, quote=quote, ccxt_symbol=candidates[0])
