from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from services.bot_engine.db import create_db_engine
from services.bot_engine.engine_state import EngineState
from services.bot_engine.events import FillEvent
from services.bot_engine.fill_handler import FillHandler
from services.bot_engine.fills_repo import FillsRepo
from services.bot_engine.positions_repo import PositionsRepo
from services.execution.exchange_client import ExecutionClient, ExecutionClientConfig
from services.execution.intent_registry import OrderIntentRegistry
from services.execution.models import NormalizedOrderRequest
from services.execution.transport_ccxt import CcxtAsyncTransport, TransportConfig
from services.execution.symbols import resolve_ccxt_symbol

from .settings import BotSettings

logger = logging.getLogger("bot_runtime.smoke")


@dataclass(frozen=True, slots=True)
class SmokeResult:
    opened_trade_id: str | None
    closed_trade_id: str | None
    fills_seen: int
    db_inserts: int


def _configure_logging() -> None:
    level = ( __import__("os").environ.get("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(level=logging.getLevelName(level), format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _d(x: Any) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


async def _poll_trades_until(
    *,
    client: ExecutionClient,
    symbol: str,
    since_ms: int,
    timeout_s: float,
    predicate,
) -> list[object]:
    deadline = asyncio.get_running_loop().time() + timeout_s
    cur_since = since_ms
    out: list[object] = []
    while asyncio.get_running_loop().time() < deadline:
        trades = await client.fetch_my_trades(symbol=symbol, since_ms=cur_since, limit=50)
        # advance since to last ts (ms) to reduce load
        if trades:
            last_ts = max(int(t.ts.timestamp() * 1000) for t in trades)
            cur_since = max(cur_since, last_ts)
        for t in trades:
            if predicate(t):
                out.append(t)
        if out:
            return out
        await asyncio.sleep(1.0)
    return out


async def _trade_sync_once(
    *,
    client: ExecutionClient,
    handler: FillHandler,
    bot_run_id: str,
    position_mode: str,
    since_ms: int,
    window_ms: int,
) -> int:
    # Pull all trades in (since_ms - window_ms .. now), apply idempotently.
    pull_since = max(0, since_ms - window_ms)
    trades = await client.fetch_my_trades(symbol=None, since_ms=pull_since, limit=200)
    inserts = 0
    for nf in trades:
        ev = _normalized_fill_to_event(bot_run_id=bot_run_id, fill=nf)
        if ev.position_side is None:
            continue
        res = handler.process_fill(fill=ev, position_mode=position_mode, position_side=ev.position_side)
        inserts += 1 if res.inserted else 0
    return inserts


def _normalized_fill_to_event(*, bot_run_id: str, fill) -> FillEvent:
    return FillEvent(
        event_id=fill.event_id,
        ts=fill.ts,
        bot_run_id=bot_run_id,
        exchange=fill.exchange,
        symbol=fill.symbol,
        exchange_trade_id=fill.exchange_trade_id,
        order_id=None,
        side=fill.side,
        position_side=fill.position_side,
        price=fill.price,
        qty=fill.qty,
        quote_qty=fill.quote_qty,
        fee_cost=fill.fee_cost,
        fee_currency=fill.fee_currency,
        is_maker=fill.is_maker,
        margin_mode=fill.margin_mode,
        leverage=fill.leverage,
        collateral_asset=fill.collateral_asset,
    )


async def run_smoke_trading(*, settings: BotSettings) -> SmokeResult:
    _configure_logging()

    if not settings.run_id:
        raise RuntimeError("RUN_ID env var is required for smoke (bot_run_id)")

    # --- DB engine & handler
    engine = create_db_engine(settings.database_url)

    # Ensure bot_run exists (smoke uses RUN_ID directly).
    # In production bot_run is created by platform backend before starting runtime container.
    from sqlalchemy import text  # local import to keep smoke module lightweight

    with engine.begin() as conn:
        # Create minimal bot + config rows for FK integrity in local smoke.
        conn.execute(
            text(
                """
                INSERT INTO bots (id, user_id, created_by_user_id, name, bot_name, exchange, market, status)
                VALUES (:id, :user_id, :created_by_user_id, :name, :bot_name, :exchange, :market, :status)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "created_by_user_id": "00000000-0000-0000-0000-000000000001",
                "name": "local-smoke-bot",
                "bot_name": "local_smoke_bot",
                "exchange": settings.bot.exchange,
                "market": "futures",
                "status": "running",
            },
        )

        conn.execute(
            text(
                """
                INSERT INTO bot_configs (id, bot_id, version, config_body)
                VALUES (:id, :bot_id, :version, CAST(:config_body AS jsonb))
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "bot_id": "00000000-0000-0000-0000-000000000001",
                "version": 1,
                "config_body": "{}",
            },
        )

        conn.execute(
            text(
                """
                INSERT INTO bot_runs (id, bot_id, config_id, state, started_at)
                VALUES (:id, :bot_id, :config_id, :state, now())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": settings.run_id,
                "bot_id": "00000000-0000-0000-0000-000000000001",
                "config_id": "00000000-0000-0000-0000-000000000001",
                "state": "running",
            },
        )

    state = EngineState(engine)
    handler = FillHandler(
        state=state,
        fills_repo=FillsRepo(engine),
        positions_repo=PositionsRepo(engine),
    )

    # --- Exchange execution context
    transport = CcxtAsyncTransport(
        cfg=TransportConfig(
            exchange_id=settings.bot.exchange,
            api_key=settings.secrets.api_key,
            api_secret=settings.secrets.api_secret,
            api_passphrase=settings.secrets.api_password,
            testnet=((__import__("os").environ.get("SANDBOX") or "false").lower() == "true"),
            default_type="swap",
        )
    )
    await transport.open()
    try:
        intents = OrderIntentRegistry()
        client = ExecutionClient(
            cfg=ExecutionClientConfig(exchange_id=settings.bot.exchange, position_mode=settings.position_mode),
            transport=transport,
            intents=intents,
        )

        sym = resolve_ccxt_symbol(
            markets=transport.markets(),
            base=settings.bot.base_coin,
            quote=settings.bot.quote_coin,
            market=settings.bot.market,
        )
        symbol = sym.ccxt_symbol
        # NOTE:
        # Keep notional low to avoid InsufficientFunds on small test balances.
        # Still must satisfy min amount (ETH often ~ 0.01).
        notional = Decimal("25")

        logger.info("Smoke start", extra={"symbol": symbol, "notional": str(notional), "mode": settings.position_mode})

        # --- Price: derive qty from last 1m candle close (REST OHLCV, stable)
        now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        ohlcv = await transport.fetch_ohlcv(symbol=symbol, timeframe="1m", since=None, limit=1, params={})
        if not ohlcv:
            raise RuntimeError("failed to fetch ohlcv for qty derivation")
        last = ohlcv[-1]
        last_close = Decimal(str(last[4]))
        # Round to a safe amount precision for Bybit (0.01 for ETH/USDT:USDT in the error we saw).
        qty = (notional / last_close).quantize(Decimal("0.01"))
        if qty <= 0:
            raise RuntimeError("qty computed <= 0")

        if qty < Decimal("0.01"):
            raise RuntimeError(f"qty computed < min (0.01): {qty}")

        # --- OPEN LONG (market)
        open_coid = f"smoke-open-{uuid.uuid4().hex[:16]}"
        open_req = NormalizedOrderRequest(
            exchange=settings.bot.exchange,
            symbol=symbol,
            type="market",
            side="buy",
            amount=qty,
            price=None,
            position_mode=settings.position_mode,
            position_side="LONG",
            reduce_only=False,
            client_order_id=open_coid,
            extra={},
        )
        o = await client.create_order(open_req)
        logger.info("Order submitted (open)", extra={"client_order_id": open_coid, "exchange_order_id": o.exchange_order_id})

        # wait for OPEN fill, then persist via FillHandler (idempotent)
        since_ms = now_ms - 60_000
        open_trades = await _poll_trades_until(
            client=client,
            symbol=symbol,
            since_ms=since_ms,
            timeout_s=60,
            predicate=lambda t: getattr(t, "client_order_id", None) == open_coid,
        )
        db_inserts = 0
        opened_trade_id = None
        for nf in open_trades:
            ev = _normalized_fill_to_event(bot_run_id=settings.run_id, fill=nf)
            if ev.position_side is None:
                logger.error("Fill missing position_side; skipping", extra={"exchange_trade_id": ev.exchange_trade_id})
                continue
            res = handler.process_fill(fill=ev, position_mode=settings.position_mode, position_side=ev.position_side)
            logger.info(
                "Fill processed (open)",
                extra={
                    "exchange_trade_id": ev.exchange_trade_id,
                    "inserted": res.inserted,
                    "position_id": res.position_id,
                    "snapshot_id": res.snapshot_id,
                    "new_qty": str(res.new_state.qty),
                    "realized_delta": str(res.realized_delta),
                },
            )
            print(
                "OPEN_FILL_RESULT",
                {
                    "exchange_trade_id": ev.exchange_trade_id,
                    "inserted": res.inserted,
                    "position_id": res.position_id,
                    "snapshot_id": res.snapshot_id,
                    "new_qty": str(res.new_state.qty),
                    "realized_delta": str(res.realized_delta),
                },
                flush=True,
            )
            db_inserts += 1 if res.inserted else 0
            opened_trade_id = ev.exchange_trade_id if opened_trade_id is None else opened_trade_id

        # --- CLOSE LONG reduceOnly (market) using same qty
        close_coid = f"smoke-close-{uuid.uuid4().hex[:16]}"
        close_req = NormalizedOrderRequest(
            exchange=settings.bot.exchange,
            symbol=symbol,
            type="market",
            side="sell",
            amount=qty,
            price=None,
            position_mode=settings.position_mode,
            position_side="LONG",
            reduce_only=True,
            client_order_id=close_coid,
            extra={},
        )
        c = await client.create_order(close_req)
        logger.info("Order submitted (close)", extra={"client_order_id": close_coid, "exchange_order_id": c.exchange_order_id})

        close_trades = await _poll_trades_until(
            client=client,
            symbol=symbol,
            since_ms=since_ms,
            timeout_s=60,
            predicate=lambda t: getattr(t, "client_order_id", None) == close_coid,
        )
        closed_trade_id = None
        for nf in close_trades:
            ev = _normalized_fill_to_event(bot_run_id=settings.run_id, fill=nf)
            if ev.position_side is None:
                logger.error("Fill missing position_side; skipping", extra={"exchange_trade_id": ev.exchange_trade_id})
                continue
            res = handler.process_fill(fill=ev, position_mode=settings.position_mode, position_side=ev.position_side)
            logger.info(
                "Fill processed (close)",
                extra={
                    "exchange_trade_id": ev.exchange_trade_id,
                    "inserted": res.inserted,
                    "position_id": res.position_id,
                    "snapshot_id": res.snapshot_id,
                    "new_qty": str(res.new_state.qty),
                    "realized_delta": str(res.realized_delta),
                },
            )
            print(
                "CLOSE_FILL_RESULT",
                {
                    "exchange_trade_id": ev.exchange_trade_id,
                    "inserted": res.inserted,
                    "position_id": res.position_id,
                    "snapshot_id": res.snapshot_id,
                    "new_qty": str(res.new_state.qty),
                    "realized_delta": str(res.realized_delta),
                },
                flush=True,
            )
            db_inserts += 1 if res.inserted else 0
            closed_trade_id = ev.exchange_trade_id if closed_trade_id is None else closed_trade_id

        fills_seen = len(open_trades) + len(close_trades)
        logger.info(
            "Smoke done",
            extra={
                "fills_seen": fills_seen,
                "db_inserts": db_inserts,
                "opened_trade_id": opened_trade_id,
                "closed_trade_id": closed_trade_id,
            },
        )

        # Safety-net: sync all trades in last 5 minutes to capture any manual user actions.
        db_inserts += await _trade_sync_once(
            client=client,
            handler=handler,
            bot_run_id=settings.run_id,
            position_mode=settings.position_mode,
            since_ms=now_ms,
            window_ms=5 * 60_000,
        )

        return SmokeResult(
            opened_trade_id=opened_trade_id,
            closed_trade_id=closed_trade_id,
            fills_seen=fills_seen,
            db_inserts=db_inserts,
        )
    finally:
        await transport.close()
