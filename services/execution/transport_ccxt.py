from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .errors import OrderRejectedError, RateLimitError, TemporaryNetworkError


@dataclass(frozen=True, slots=True)
class TransportConfig:
    exchange_id: str
    api_key: Optional[str]
    api_secret: Optional[str]
    api_passphrase: Optional[str]
    testnet: bool = False

    # Futures context (ccxt options vary per exchange)
    default_type: str = "swap"  # "swap" (perp) / "future"
    enable_rate_limit: bool = True

    request_timeout_ms: int = 20_000
    retries: int = 2
    retry_backoff_base_s: float = 0.5


class CcxtAsyncTransport:
    """Thin async transport wrapper around ccxt.async_support.

    Responsibilities:
    - create and own ccxt exchange instance
    - set common options (defaultType, timeouts, enableRateLimit)
    - map common ccxt exceptions to our domain errors
    - provide a single place for retries/backoff
    - expose loaded markets metadata (precision/limits/contractSize) for order normalization
    """

    def __init__(self, *, cfg: TransportConfig, adapter_opts: Optional[Mapping[str, Any]] = None):
        self._cfg = cfg
        self._adapter_opts = dict(adapter_opts or {})
        self._exchange = None
        self._session = None

    async def open(self) -> None:
        # Import lazily to keep services install flexible.
        import ccxt.async_support as ccxt  # type: ignore
        import aiohttp
        from aiohttp.resolver import ThreadedResolver

        ex_class = getattr(ccxt, self._cfg.exchange_id, None)
        if ex_class is None:
            raise ValueError(f"ccxt exchange not found: {self._cfg.exchange_id}")

        opts: dict[str, Any] = {
            **self._adapter_opts,
            "apiKey": self._cfg.api_key,
            "secret": self._cfg.api_secret,
            "password": self._cfg.api_passphrase,
            "enableRateLimit": self._cfg.enable_rate_limit,
            "timeout": self._cfg.request_timeout_ms,
            "options": {
                "defaultType": self._cfg.default_type,
            },
        }

        # Merge nested options (adapter may provide per-exchange 'options' flags).
        if "options" in self._adapter_opts and isinstance(self._adapter_opts.get("options"), dict):
            opts.setdefault("options", {})
            opts["options"] = {**self._adapter_opts["options"], **opts["options"]}

        # Force ThreadedResolver to avoid aiodns/AsyncResolver DNS issues seen on some Windows setups.
        # NOTE: ccxt uses aiohttp under the hood; providing a prebuilt session makes DNS behavior explicit.
        # IMPORTANT: If we pass a prebuilt session to ccxt, we must close it ourselves.
        # Let ccxt manage its own aiohttp session.
        # (Passing a custom session requires perfect lifecycle integration and can lead to unclosed-session warnings.)
        self._exchange = ex_class(opts)

        # best-effort testnet toggle (exchange-specific in reality)
        if self._cfg.testnet and hasattr(self._exchange, "set_sandbox_mode"):
            self._exchange.set_sandbox_mode(True)

        try:
            await self._exchange.load_markets()
        except Exception:
            # ensure aiohttp connector is closed even if load_markets fails (e.g., auth error)
            try:
                await self._exchange.close()
            finally:
                self._exchange = None
                if self._session is not None:
                    await self._session.close()
                    self._session = None
            raise

    async def close(self) -> None:
        if self._exchange is not None:
            try:
                await self._exchange.close()
            finally:
                self._exchange = None

        # No custom session is used (ccxt manages its own aiohttp session internally).
        self._session = None

    def markets(self) -> Mapping[str, Any]:
        """Return ccxt markets dict.

        NOTE:
        - Works only after open() (load_markets executed).
        - Read-only use is expected (do not mutate).
        """
        if self._exchange is None:
            raise RuntimeError("transport is not open()")
        return self._exchange.markets  # type: ignore[no-any-return]

    def market(self, symbol: str) -> Mapping[str, Any]:
        """Return ccxt market metadata for symbol.

        NOTE:
        - Works only after open() (load_markets executed).
        - For swap/futures some exchanges use symbol formatting like "BTC/USDT:USDT".
          Normalization of symbol strings is handled upstream; this function expects a ccxt-valid symbol.
        """
        if self._exchange is None:
            raise RuntimeError("transport is not open()")
        return self._exchange.market(symbol)  # type: ignore[no-any-return]

    async def create_order(
        self,
        *,
        symbol: str,
        type: str,
        side: str,
        amount: Any,
        price: Any = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        return await self._call(
            "create_order",
            symbol,
            type,
            side,
            amount,
            price,
            params or {},
        )

    async def cancel_order(
        self, *, order_id: str, symbol: Optional[str] = None, params: Optional[Mapping[str, Any]] = None
    ) -> Mapping[str, Any]:
        if symbol is None:
            return await self._call("cancel_order", order_id, None, params or {})
        return await self._call("cancel_order", order_id, symbol, params or {})

    async def fetch_open_orders(
        self, *, symbol: Optional[str] = None, params: Optional[Mapping[str, Any]] = None
    ) -> list[Mapping[str, Any]]:
        res = await self._call("fetch_open_orders", symbol, None, None, None, params or {})
        return list(res)  # type: ignore[arg-type]

    async def fetch_order(
        self, *, order_id: str, symbol: Optional[str] = None, params: Optional[Mapping[str, Any]] = None
    ) -> Mapping[str, Any]:
        return await self._call("fetch_order", order_id, symbol, params or {})

    async def fetch_my_trades(
        self,
        *,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[Mapping[str, Any]]:
        res = await self._call("fetch_my_trades", symbol, since, limit, params or {})
        return list(res)  # type: ignore[arg-type]

    async def fetch_positions(
        self, *, symbols: Optional[list[str]] = None, params: Optional[Mapping[str, Any]] = None
    ) -> list[Mapping[str, Any]]:
        res = await self._call("fetch_positions", symbols, params or {})
        return list(res)  # type: ignore[arg-type]

    async def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> list[list[Any]]:
        res = await self._call("fetch_ohlcv", symbol, timeframe, since, limit, params or {})
        return list(res)  # type: ignore[arg-type]

    async def _call(self, method: str, *args: Any) -> Any:
        if self._exchange is None:
            raise RuntimeError("transport is not open()")

        last_exc: Exception | None = None

        for attempt in range(self._cfg.retries + 1):
            try:
                fn = getattr(self._exchange, method)
                return await fn(*args)
            except Exception as e:  # noqa: BLE001
                last_exc = e
                if self._is_rate_limit(e):
                    raise RateLimitError(str(e)) from e
                if self._is_reject(e):
                    raise OrderRejectedError(str(e)) from e
                if self._is_temporary(e) and attempt < self._cfg.retries:
                    await asyncio.sleep(self._cfg.retry_backoff_base_s * (2**attempt))
                    continue
                # Non-temporary errors should not be mapped to TemporaryNetworkError (e.g. InsufficientFunds).
                raise

        raise TemporaryNetworkError(str(last_exc)) from last_exc

    @staticmethod
    def _is_rate_limit(e: Exception) -> bool:
        # ccxt uses many subclasses; safest check is message heuristics.
        msg = str(e).lower()
        return "rate limit" in msg or "too many requests" in msg or "429" in msg

    @staticmethod
    def _is_reject(e: Exception) -> bool:
        msg = str(e).lower()
        return "order" in msg and ("rejected" in msg or "insufficient" in msg)

    @staticmethod
    def _is_temporary(e: Exception) -> bool:
        msg = str(e).lower()
        return any(s in msg for s in ["timeout", "temporarily", "network", "connection reset", "service unavailable"])
