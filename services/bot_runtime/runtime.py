from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from decimal import Decimal

from .candle_store import CandleStore, TimeframeState
from .candles_ws import WsCandlesClient, WsCandlesStream
from .indicator_pipeline import IndicatorConfig, IndicatorPipeline
from .signal_resolver import recompute_all
from .signal_store import SignalStore
from .mock_candles import MockCandlesStream
from .price_feed import PriceFeed, PriceStatus
from services.bot_engine.bootstrap_sync import BootstrapSync, map_ccxt_position_to_bootstrap
from services.bot_engine.db import create_db_engine
from services.execution.exchange_client import ExecutionClient, ExecutionClientConfig
from services.execution.adapters.registry import get_adapter
from services.execution.intent_registry import OrderIntentRegistry
from services.execution.transport_ccxt import CcxtAsyncTransport, TransportConfig
from services.execution.ohlcv_client import OhlcvRestClient, OhlcvRequest
from services.execution.symbols import resolve_ccxt_symbol

from services.bot_engine.engine_state import EngineState
from services.bot_engine.events import FillEvent
from services.bot_engine.fill_handler import FillHandler
from services.bot_engine.fills_repo import FillsRepo
from services.bot_engine.positions_repo import PositionsRepo
from services.bot_engine.positions_reader import PositionsReader
from services.bot_engine.orders_repo import OrdersRepo
from services.bot_engine.order_manager import OrderManager
from services.bot_engine.strategy import StrategySupervisor
from services.bot_engine.deals_repo import DealsRepo
from services.bot_engine.exit_tracker import ExitTracker
from services.bot_engine.dynamic_averaging import AveragingConfig, AveragingCoordinator

from .settings import BotSettings


logger = logging.getLogger("bot_runtime")


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    phase: str
    ts: datetime
    detail: str | None = None


class BotRuntime:
    """Single-bot container runtime.

    This is a lifecycle coordinator. It will be extended to wire:
    - WS candles client (bootstrap >= 300)
    - indicator pipeline
    - execution gateway
    - bootstrap sync + reconciliation
    - fills ingest
    - strategy supervisor
    """

    def __init__(self, *, settings: BotSettings):
        self._settings = settings
        self._tasks: list[asyncio.Task[object]] = []
        self._stopped = asyncio.Event()
        self._status = RuntimeStatus(phase="created", ts=datetime.now(timezone.utc))

    async def start(self) -> None:
        self._configure_logging()

        run_id = self._settings.run_id or str(uuid.uuid4())
        # Bootstrap current positions into DB. In offline/dev environments, exchange may be unavailable.
        # IMPORTANT: this must be after settings are fully loaded; mock mode should never call exchange.
        if self._settings.market_data_source == "mock":
            logger.info("Bootstrap sync disabled in mock market data mode", extra={"run_id": run_id})
        else:
            try:
                await self._bootstrap_sync_positions(run_id=run_id)
            except Exception:
                logger.exception("Bootstrap sync skipped due to error", extra={"run_id": run_id})

        logger.info(
            "Starting bot runtime",
            extra={
                "bot_id": self._settings.bot_id,
                "run_id": run_id,
                "exchange": self._settings.bot.exchange,
                "symbol": self._settings.symbol,
                "timeframes": self._settings.working_timeframes,
            },
        )

        # Canonical symbol in config/runtime is spot-like: "BTC/USDT".
        # For CCXT swap/futures some exchanges require "BTC/USDT:USDT".
        self._ccxt_symbol = self._settings.symbol
        if self._settings.market_data_source != "mock":
            try:
                md_transport = CcxtAsyncTransport(
                    cfg=TransportConfig(
                        exchange_id=self._settings.bot.exchange,
                        api_key=self._settings.secrets.api_key,
                        api_secret=self._settings.secrets.api_secret,
                        api_passphrase=self._settings.secrets.api_password,
                        testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                        default_type="swap",
                    )
                )
                await md_transport.open()
                try:
                    sym = resolve_ccxt_symbol(
                        markets=md_transport.markets(),
                        base=self._settings.bot.base_coin,
                        quote=self._settings.bot.quote_coin,
                        market=self._settings.bot.market,
                    )
                    self._ccxt_symbol = sym.ccxt_symbol
                finally:
                    await md_transport.close()
            except Exception:
                logger.exception(
                    "CCXT symbol resolve failed; falling back to canonical symbol",
                    extra={"bot_id": self._settings.bot_id, "symbol": self._settings.symbol},
                )
                self._ccxt_symbol = self._settings.symbol

        self._status = RuntimeStatus(phase="starting", ts=datetime.now(timezone.utc))

        candle_store = CandleStore()
        tf_states = [
            TimeframeState(timeframe=tf, maxlen=350, required_bars=300) for tf in self._settings.working_timeframes
        ]
        for s in tf_states:
            candle_store.ensure(symbol=self._settings.symbol, tf_state=s)

        price_feed = PriceFeed(store=candle_store, stale_after_seconds=30)

        if self._settings.market_data_source == "mock":
            ws = MockCandlesStream(
                symbol=self._settings.symbol,
                start_price=Decimal(self._settings.mock_start_price),
                seed=self._settings.mock_seed,
                speedup=self._settings.mock_speedup,
            )

            # Fast warmup for development: prefill history so warmup completes quickly even on large TFs.
            for s in tf_states:
                for ev in ws.bootstrap(timeframe=s.timeframe, bars=s.required_bars):
                    candle_store.upsert(ev.candle)
        else:
            # REST warmup fallback: preload required bars to allow trading even if WS is unstable.
            try:
                md_adapter = get_adapter(exchange_id=self._settings.bot.exchange)
                rest_transport = CcxtAsyncTransport(
                    cfg=TransportConfig(
                        exchange_id=self._settings.bot.exchange,
                        api_key=self._settings.secrets.api_key,
                        api_secret=self._settings.secrets.api_secret,
                        api_passphrase=self._settings.secrets.api_password,
                        testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                        default_type="swap",
                    ),
                    adapter_opts=md_adapter.ccxt_options(
                        TransportConfig(
                            exchange_id=self._settings.bot.exchange,
                            api_key=self._settings.secrets.api_key,
                            api_secret=self._settings.secrets.api_secret,
                            api_passphrase=self._settings.secrets.api_password,
                            testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                            default_type="swap",
                        )
                    ),
                )
                await rest_transport.open()
                try:
                    ohlcv = OhlcvRestClient(transport=rest_transport)
                    for s in tf_states:
                        candles = await ohlcv.fetch_history(
                            OhlcvRequest(symbol=self._ccxt_symbol, timeframe=s.timeframe, limit=s.required_bars)
                        )
                        for c in candles:
                            candle_store.upsert(c)
                    logger.info("REST warmup complete", extra={"bot_id": self._settings.bot_id})
                finally:
                    await rest_transport.close()
            except Exception:
                logger.exception("REST warmup failed", extra={"bot_id": self._settings.bot_id})

            ws = WsCandlesStream(
                client=WsCandlesClient(
                    url=self._settings.candles_ws_url,
                    exchange=self._settings.bot.exchange,
                    symbol=self._ccxt_symbol,
                )
            )

        indicators = IndicatorPipeline(
            store=candle_store,
            symbol=self._settings.symbol,
            cfg=IndicatorConfig(timeframe=self._settings.entry.entry_timeframe),
        )

        signals = SignalStore()

        self._tasks.append(asyncio.create_task(self._ws_ingest(ws=ws, store=candle_store, tf_states=tf_states)))
        self._tasks.append(asyncio.create_task(self._rest_candles_fallback_loop(store=candle_store, tf_states=tf_states), name="rest_candles_fallback"))
        self._tasks.append(asyncio.create_task(self._warmup_gate(store=candle_store, tf_states=tf_states)))
        self._tasks.append(asyncio.create_task(indicators.run(), name="indicators"))
        self._tasks.append(
            asyncio.create_task(
                self._signals_loop(store=candle_store, signals=signals),
                name="signals",
            )
        )
        self._tasks.append(
            asyncio.create_task(
                self._price_guard_loop(store=candle_store, price_feed=price_feed),
                name="price_guard",
            )
        )
        if self._settings.market_data_source == "mock":
            logger.info("fills_ingest disabled in mock market data mode", extra={"bot_id": self._settings.bot_id})
        else:
            self._tasks.append(asyncio.create_task(self._fills_ingest_loop(run_id=run_id), name="fills_ingest"))
        self._tasks.append(
            asyncio.create_task(
                self._strategy_loop(run_id=run_id, price_feed=price_feed, signals=signals),
                name="strategy",
            )
        )
        self._tasks.append(asyncio.create_task(self._heartbeat_loop(), name="heartbeat"))

        self._status = RuntimeStatus(phase="running", ts=datetime.now(timezone.utc))

    async def stop(self) -> None:
        logger.info("Stopping bot runtime", extra={"bot_id": self._settings.bot_id})

        self._status = RuntimeStatus(phase="stopping", ts=datetime.now(timezone.utc))

        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        self._status = RuntimeStatus(phase="stopped", ts=datetime.now(timezone.utc))
        self._stopped.set()

    async def _bootstrap_sync_positions(self, *, run_id: str) -> None:
        # Bootstrap current exchange positions into our DB snapshots so engine isn't blind
        # to real exposure after restart/manual trades.
        engine = create_db_engine(self._settings.database_url)

        transport = CcxtAsyncTransport(
            cfg=TransportConfig(
                exchange_id=self._settings.bot.exchange,
                api_key=self._settings.secrets.api_key,
                api_secret=self._settings.secrets.api_secret,
                api_passphrase=self._settings.secrets.api_password,
                testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                default_type="swap",
            )
        )

        await transport.open()
        try:
            raw_positions = await transport.fetch_positions(symbols=None, params={})
            bps = [
                map_ccxt_position_to_bootstrap(p=p, exchange=self._settings.bot.exchange, position_mode=self._settings.position_mode)
                for p in raw_positions
                if (p.get("contracts") or 0) not in (0, 0.0)
            ]
            inserted = BootstrapSync(engine).sync_positions(bot_run_id=run_id, positions_in=bps)
            if inserted:
                logger.info("Bootstrap sync done", extra={"run_id": run_id, "snapshots_inserted": inserted})
        except Exception:
            logger.exception("Bootstrap sync failed", extra={"run_id": run_id})
        finally:
            await transport.close()

    def _configure_logging(self) -> None:
        # LOG_LEVEL comes from env as a string; normalize to int level.
        raw = (__import__("os").environ.get("LOG_LEVEL") or "INFO").strip().upper()
        level = logging._nameToLevel.get(raw, logging.INFO)
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    async def _ws_ingest(self, *, ws: WsCandlesStream, store: CandleStore, tf_states: list[TimeframeState]) -> None:
        """Run one task per timeframe and upsert into store."""
        async def _run_tf(tf: str) -> None:
            async for ev in ws.stream_timeframe(timeframe=tf):
                store.upsert(ev.candle)

        tasks = [asyncio.create_task(_run_tf(s.timeframe), name=f"ws:{s.timeframe}") for s in tf_states]
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _rest_candles_fallback_loop(self, *, store: CandleStore, tf_states: list[TimeframeState]) -> None:
        """If WS stops updating candles, poll latest candle via REST once per minute.

        Policy (per user request):
          - WS down/stale => update once at the beginning of each minute (approx)
        """
        if self._settings.market_data_source == "mock":
            return

        # Dedicated REST transport for market data to decouple from WS.
        transport = CcxtAsyncTransport(
            cfg=TransportConfig(
                exchange_id=self._settings.bot.exchange,
                api_key=self._settings.secrets.api_key,
                api_secret=self._settings.secrets.api_secret,
                api_passphrase=self._settings.secrets.api_password,
                testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                default_type="swap",
            )
        )
        await transport.open()
        try:
            ohlcv = OhlcvRestClient(transport=transport)
            symbol = self._ccxt_symbol

            while True:
                # Sleep until the next minute boundary.
                now = datetime.now(tz=timezone.utc)
                sleep_s = 60 - now.second - (now.microsecond / 1_000_000)
                if sleep_s < 0.05:
                    sleep_s = 0.05
                await asyncio.sleep(sleep_s)

                # If WS is healthy (fresh candles), do nothing.
                st = self._price_feed_status_for_rest_guard(store=store)
                if st:
                    continue

                for s in tf_states:
                    try:
                        c = await ohlcv.fetch_latest(symbol=symbol, timeframe=s.timeframe)
                        store.upsert(c)
                    except Exception:
                        logger.exception(
                            "REST candle poll failed",
                            extra={"bot_id": self._settings.bot_id, "symbol": symbol, "tf": s.timeframe},
                        )
        except asyncio.CancelledError:
            raise
        finally:
            await transport.close()

    def _price_feed_status_for_rest_guard(self, *, store: CandleStore) -> bool:
        # Consider WS healthy if 1m latest candle was updated within stale window.
        # We reuse CandleStore timestamps to avoid depending on PriceFeed instance in this loop.
        last_ms = store.last_update_ms(symbol=self._settings.symbol, timeframe="1m")
        if last_ms is None:
            return False
        age_s = (int(datetime.now(tz=timezone.utc).timestamp() * 1000) - int(last_ms)) / 1000.0
        return age_s <= 35.0

    async def _warmup_gate(self, *, store: CandleStore, tf_states: list[TimeframeState]) -> None:
        self._status = RuntimeStatus(phase="warming_up", ts=datetime.now(timezone.utc))
        while True:
            if all(store.is_warmed_up(symbol=self._settings.symbol, tf_state=s) for s in tf_states):
                self._status = RuntimeStatus(phase="ready", ts=datetime.now(timezone.utc))
                logger.info("Warmup ready", extra={"bot_id": self._settings.bot_id})
                return
            await asyncio.sleep(0.2)

    async def _price_guard_loop(self, *, store: CandleStore, price_feed: PriceFeed) -> None:
        """Continuously checks if we have a usable (fresh) price.

        For now it's a placeholder to wire the guard policy; strategy/execution
        will consult the same PriceFeed before issuing entry/avg intents.
        """
        last_state: str | None = None
        while True:
            st: PriceStatus = price_feed.status(symbol=self._settings.symbol)
            state = "ok" if st.ok else "no_price"

            if state != last_state:
                last_state = state
                logger.info(
                    "Price guard state",
                    extra={
                        "bot_id": self._settings.bot_id,
                        "symbol": self._settings.symbol,
                        "state": state,
                        "reason": st.reason,
                        "tf": "1m",
                        "last_update_ms": st.last_update_ms,
                    },
                )

            await asyncio.sleep(1.0)

    async def _fills_ingest_loop(self, *, run_id: str) -> None:
        """Poll user trades and apply them idempotently into DB snapshots via FillHandler.

        MVP:
          - uses fetch_my_trades(symbol=None) to keep it simple
          - relies on uq_trade_fills_exchange_symbol_trade_id for de-dup
          - stores minimal position math (WA) into positions/snapshots
        """
        engine = create_db_engine(self._settings.database_url)
        state = EngineState(engine)
        exit_tracker = ExitTracker()
        handler = FillHandler(
            state=state,
            fills_repo=FillsRepo(engine),
            positions_repo=PositionsRepo(engine),
            deals_repo=DealsRepo(engine),
            exit_tracker=exit_tracker,
        )

        transport = CcxtAsyncTransport(
            cfg=TransportConfig(
                exchange_id=self._settings.bot.exchange,
                api_key=self._settings.secrets.api_key,
                api_secret=self._settings.secrets.api_secret,
                api_passphrase=self._settings.secrets.api_password,
                testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                default_type="swap",
            )
        )

        await transport.open()
        try:
            intents = OrderIntentRegistry()
            adapter = get_adapter(exchange_id=self._settings.bot.exchange)
            adapter.bind_markets(markets=transport.markets())
            adapter.bind_symbol(base=self._settings.bot.base_coin, quote=self._settings.bot.quote_coin)
            client = ExecutionClient(
                cfg=ExecutionClientConfig(position_mode=self._settings.position_mode),
                adapter=adapter,
                transport=transport,
                intents=intents,
            )

            # Start window: last 5 minutes (conservative) to survive small clock skews.
            since_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000) - 5 * 60_000

            while True:
                trades = await client.fetch_my_trades(symbol=None, since_ms=since_ms, limit=200)
                if trades:
                    # move since to newest trade ts to reduce load
                    last_ts = max(int(t.ts.timestamp() * 1000) for t in trades)
                    since_ms = max(since_ms, last_ts)

                inserted = 0
                for nf in trades:
                    raw_exit_reason = None
                    if isinstance(nf.raw, dict):
                        raw_exit_reason = nf.raw.get("_exit_reason")

                    ev = FillEvent(
                        event_id=nf.event_id,
                        ts=nf.ts,
                        bot_run_id=run_id,
                        exchange=nf.exchange,
                        symbol=nf.symbol,
                        exchange_trade_id=nf.exchange_trade_id,
                        order_id=None,
                        exchange_order_id=nf.exchange_order_id,
                        client_order_id=nf.client_order_id,
                        exit_reason=str(raw_exit_reason) if raw_exit_reason is not None else None,
                        side=nf.side,
                        position_side=nf.position_side,
                        price=nf.price,
                        qty=nf.qty,
                        quote_qty=nf.quote_qty,
                        fee_cost=nf.fee_cost,
                        fee_currency=nf.fee_currency,
                        is_maker=nf.is_maker,
                        margin_mode=nf.margin_mode,
                        leverage=nf.leverage,
                        collateral_asset=nf.collateral_asset,
                    )
                    if ev.position_side is None:
                        continue

                    res = handler.process_fill(fill=ev, position_mode=self._settings.position_mode, position_side=ev.position_side)
                    inserted += 1 if res.inserted else 0

                if inserted:
                    logger.info(
                        "Fills ingested",
                        extra={"bot_id": self._settings.bot_id, "run_id": run_id, "inserted": inserted},
                    )

                await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("fills_ingest loop failed", extra={"bot_id": self._settings.bot_id, "run_id": run_id})
            # prevent tight crash loop
            await asyncio.sleep(5.0)
        finally:
            await transport.close()

    async def _signals_loop(self, *, store: CandleStore, signals: SignalStore) -> None:
        # Recompute latest signals periodically (cheap), based on current CandleStore.
        while True:
            try:
                recompute_all(self._settings, store, signals, symbol=self._settings.symbol)
            except Exception:
                logger.exception("signals loop failed", extra={"bot_id": self._settings.bot_id})
            await asyncio.sleep(0.5)

    async def _strategy_loop(self, *, run_id: str, price_feed: PriceFeed, signals: SignalStore) -> None:
        """Strategy + order reconcile loop.

        MVP: only maintains TP conditional reduceOnly order based on current position WA entry.
        """
        # Enable strategy in mock mode as well (for local smoke tests).
        # Execution/transport may still be mocked at a lower layer.

        engine = create_db_engine(self._settings.database_url)

        # Execution context
        transport = CcxtAsyncTransport(
            cfg=TransportConfig(
                exchange_id=self._settings.bot.exchange,
                api_key=self._settings.secrets.api_key,
                api_secret=self._settings.secrets.api_secret,
                api_passphrase=self._settings.secrets.api_password,
                testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
                default_type="swap",
            )
        )
        await transport.open()
        try:
            intents = OrderIntentRegistry()
            adapter = get_adapter(exchange_id=self._settings.bot.exchange)
            adapter.bind_markets(markets=transport.markets())
            adapter.bind_symbol(base=self._settings.bot.base_coin, quote=self._settings.bot.quote_coin)
            client = ExecutionClient(
                cfg=ExecutionClientConfig(position_mode=self._settings.position_mode),
                adapter=adapter,
                transport=transport,
                intents=intents,
            )

            avg_cfg = AveragingConfig(
                range_cover_pct=Decimal(str(self._settings.grid.range_cover)),
                first_so_coeff=self._settings.grid.first_so_coeff,
                dynamic_so_coeff=self._settings.grid.dynamic_so_coeff,
                new_order_time_s=int(self._settings.averaging.new_order_time),
                poll_s=float(self._settings.averaging.avg_timesleep),
            )

            avg = AveragingCoordinator(
                bot_id=self._settings.bot_id,
                exchange=self._settings.bot.exchange,
                position_mode=self._settings.position_mode,
                cfg=avg_cfg,
                price_feed=price_feed,
                signals=signals,
                amount_resolver=lambda symbol, ps, so_index, entry, mark: self._settings.basic.bo_amount,
            )

            strategy = StrategySupervisor(settings=self._settings, price_feed=price_feed, signals=signals)
            order_manager = OrderManager(
                bot_id=self._settings.bot_id,
                bot_run_id=run_id,
                client=client,
                orders_repo=OrdersRepo(engine),
            )
            positions_reader = PositionsReader(engine)

            symbol = self._ccxt_symbol

            # Wait until warmup ready and price ok to reduce noise.
            while self._status.phase not in ("ready", "running"):
                await asyncio.sleep(0.2)

            while True:
                st = price_feed.status(symbol=self._settings.symbol)
                if not st.ok:
                    await asyncio.sleep(0.5)
                    continue

                # For MVP, only LONG+SHORT maintenance independently.
                for ps in ("LONG", "SHORT"):
                    snap = positions_reader.latest_snapshot(
                        bot_run_id=run_id,
                        symbol=self._settings.symbol,
                        position_mode=self._settings.position_mode,
                        position_side=ps,
                    )
                    # In mock mode we may not have position snapshots yet; allow FLAT logic to place BO grid.
                    if snap is None:
                        position_qty = Decimal("0")
                        avg_entry_price = None
                    else:
                        position_qty = snap.qty.copy_abs()
                        avg_entry_price = snap.avg_entry_price

                    decision = strategy.decide(
                        symbol=self._settings.symbol,
                        position_side=ps,  # type: ignore[arg-type]
                        position_qty=position_qty,
                        avg_entry_price=avg_entry_price,
                        open_orders=(),
                    )

                    # Dynamic averaging (non-blocking monitor + market order intents)
                    await avg.tick(
                        symbol=self._settings.symbol,
                        position_side=ps,  # type: ignore[arg-type]
                        position_qty=position_qty,
                        avg_entry_price=avg_entry_price,
                    )
                    decision.desired_orders.extend(
                        avg.consume_orders(symbol=self._settings.symbol, position_side=ps)  # type: ignore[arg-type]
                    )

                    open_orders = await transport.fetch_open_orders(symbol=symbol, params={})
                    await order_manager.reconcile(symbol=symbol, desired=decision.desired_orders, open_orders_raw=open_orders)

                # Dynamic sleep: when averaging is enabled and we have an open position, poll faster
                # to catch averaging/exit signals.
                sleep_s = 2.0
                if self._settings.averaging.enabled:
                    snap_long = positions_reader.latest_snapshot(
                        bot_run_id=run_id,
                        symbol=self._settings.symbol,
                        position_mode=self._settings.position_mode,
                        position_side="LONG",
                    )
                    snap_short = positions_reader.latest_snapshot(
                        bot_run_id=run_id,
                        symbol=self._settings.symbol,
                        position_mode=self._settings.position_mode,
                        position_side="SHORT",
                    )
                    if (snap_long is not None and snap_long.qty.copy_abs() > 0) or (
                        snap_short is not None and snap_short.qty.copy_abs() > 0
                    ):
                        sleep_s = float(self._settings.averaging.avg_timesleep)

                await asyncio.sleep(sleep_s)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("strategy loop failed", extra={"bot_id": self._settings.bot_id, "run_id": run_id})
            await asyncio.sleep(5.0)
        finally:
            # Ensure transport resources are released even on cancel/error to avoid aiohttp leak warnings.
            await transport.close()

    async def _heartbeat_loop(self) -> None:
        """Temporary stub heartbeat until DB heartbeat is implemented."""
        while True:
            logger.info(
                "Heartbeat",
                extra={
                    "phase": self._status.phase,
                    "bot_id": self._settings.bot_id,
                    "symbol": self._settings.symbol,
                },
            )
            await asyncio.sleep(10)
