from __future__ import annotations

from datetime import datetime, timezone
import uuid
from decimal import Decimal

from services.bot_engine.db import create_db_engine
from services.bot_engine.engine_state import EngineState
from services.bot_engine.events import FillEvent
from services.bot_engine.fill_handler import FillHandler
from services.bot_engine.fills_repo import FillsRepo
from services.bot_engine.positions_repo import PositionsRepo
from services.bot_engine.deals_repo import DealsRepo
from services.bot_engine.exit_tracker import ExitTracker


def main() -> None:
    engine = create_db_engine(__import__("os").environ.get("DATABASE_URL"))
    state = EngineState(engine)
    handler = FillHandler(
        state=state,
        fills_repo=FillsRepo(engine),
        positions_repo=PositionsRepo(engine),
        deals_repo=DealsRepo(engine),
        exit_tracker=ExitTracker(),
    )

    bot_id = "00000000-0000-0000-0000-000000000001"
    user_id = "00000000-0000-0000-0000-000000000001"
    bot_run_id = "00000000-0000-0000-0000-000000000001"
    now = datetime.now(timezone.utc)

    # Ensure minimal FK chain exists: bots -> bot_configs -> bot_runs
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO bots (id, user_id, created_by_user_id, name, bot_name, exchange, market, status)
                VALUES (:id, :user_id, :created_by_user_id, :name, :bot_name, :exchange, :market, :status)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": bot_id,
                "user_id": user_id,
                "created_by_user_id": user_id,
                "name": "Smoke Bot",
                "bot_name": "smoke_bot_1",
                "exchange": "bybit",
                "market": "swap",
                "status": "created",
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
                "id": bot_id,
                "bot_id": bot_id,
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
                "id": bot_run_id,
                "bot_id": bot_id,
                "config_id": bot_id,
                "state": "running",
            },
        )

    fills = [
        FillEvent(
            event_id=str(uuid.uuid4()),
            bot_run_id=bot_run_id,
            order_id=None,
            exchange="binance",
            symbol="BTC/USDT",
            exchange_trade_id=f"t1-{uuid.uuid4()}",
            ts=now,
            side="buy",
            position_side="LONG",
            margin_mode="isolated",
            leverage=Decimal("10"),
            collateral_asset="USDT",
            price=Decimal("100"),
            qty=Decimal("1"),
            quote_qty=None,
            fee_cost=Decimal("0.1"),
            fee_currency="USDT",
            is_maker=False,
        ),
        FillEvent(
            event_id=str(uuid.uuid4()),
            bot_run_id=bot_run_id,
            order_id=None,
            exchange="binance",
            symbol="BTC/USDT",
            exchange_trade_id=f"t2-{uuid.uuid4()}",
            ts=now,
            side="buy",
            position_side="LONG",
            margin_mode="isolated",
            leverage=Decimal("10"),
            collateral_asset="USDT",
            price=Decimal("110"),
            qty=Decimal("1"),
            quote_qty=None,
            fee_cost=Decimal("0.1"),
            fee_currency="USDT",
            is_maker=False,
        ),
        FillEvent(
            event_id=str(uuid.uuid4()),
            bot_run_id=bot_run_id,
            order_id=None,
            exchange_order_id="o3",
            client_order_id="bot-squeeze-btcusdt-long",
            exit_reason="squeeze_exit",
            exchange="binance",
            symbol="BTC/USDT",
            exchange_trade_id=f"t3-{uuid.uuid4()}",
            ts=now,
            side="sell",
            position_side="LONG",
            margin_mode="isolated",
            leverage=Decimal("10"),
            collateral_asset="USDT",
            price=Decimal("120"),
            qty=Decimal("1.5"),
            quote_qty=None,
            fee_cost=Decimal("0.1"),
            fee_currency="USDT",
            is_maker=False,
        ),
    ]

    for f in fills:
        res = handler.process_fill(fill=f, position_mode="hedge", position_side="LONG")
        print(res)


if __name__ == "__main__":
    main()
