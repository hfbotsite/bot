"""Execution layer (connector v2).

This package contains:
- normalized execution domain models (orders, fills, positions)
- async CCXT transport
- exchange adapters with hedge/dual-position normalization
- OHLCV REST client (warmup/polling building blocks)
- small registries (order intents) needed for correct positionSide attribution
"""

from .exchange_client import ExecutionClient, ExecutionClientConfig
from .hedge_normalizer import HedgeModeNormalizer, NormalizedCcxtOrderCall, PositionModeState
from .intent_registry import OrderIntent, OrderIntentRegistry
from .ohlcv import Candle, candles_from_ccxt_ohlcv
from .ohlcv_client import OhlcvRequest, OhlcvRestClient
from .position_mode_manager import PositionModeManager, PositionModePolicy
from .symbols import SymbolBuildResult, parse_base_coins, resolve_ccxt_symbol
from .transport_ccxt import CcxtAsyncTransport, TransportConfig

__all__ = [
    "Candle",
    "ExecutionClient",
    "ExecutionClientConfig",
    "HedgeModeNormalizer",
    "NormalizedCcxtOrderCall",
    "OhlcvRequest",
    "OhlcvRestClient",
    "OrderIntent",
    "OrderIntentRegistry",
    "PositionModeManager",
    "PositionModePolicy",
    "PositionModeState",
    "SymbolBuildResult",
    "TransportConfig",
    "CcxtAsyncTransport",
    "candles_from_ccxt_ohlcv",
    "parse_base_coins",
    "resolve_ccxt_symbol",
]
