from __future__ import annotations

import asyncio
import os

from services.bot_engine.bootstrap_sync import BootstrapSync, map_ccxt_position_to_bootstrap
from services.bot_engine.db import create_db_engine
from services.bot_runtime.settings import BotSettings
from services.execution.transport_ccxt import CcxtAsyncTransport, TransportConfig


async def main() -> None:
    s = BotSettings.load_from_env()
    if not s.run_id:
        raise RuntimeError("RUN_ID is required")

    engine = create_db_engine(s.database_url)

    t = CcxtAsyncTransport(
        cfg=TransportConfig(
            exchange_id=s.bot.exchange,
            api_key=s.secrets.api_key,
            api_secret=s.secrets.api_secret,
            api_passphrase=s.secrets.api_password,
            testnet=((os.environ.get("SANDBOX") or "false").lower() == "true"),
            default_type="swap",
        )
    )

    await t.open()
    try:
        # Pull all open positions from exchange (CCXT normalized).
        raw_positions = await t.fetch_positions(symbols=None, params={})
        bps = [
            map_ccxt_position_to_bootstrap(p=p, exchange=s.bot.exchange, position_mode=s.position_mode)
            for p in raw_positions
            if (p.get("contracts") or 0) not in (0, 0.0)
        ]

        ins = BootstrapSync(engine).sync_positions(bot_run_id=s.run_id, positions_in=bps)
        print(f"BOOTSTRAP_SYNC inserted_snapshots={ins}")
        for bp in bps:
            print(
                "BOOTSTRAP_POS",
                {
                    "symbol": bp.symbol,
                    "side": bp.position_side,
                    "qty": str(bp.qty),
                    "avg_entry_price": (str(bp.avg_entry_price) if bp.avg_entry_price is not None else None),
                    "mark_price": (str(bp.mark_price) if bp.mark_price is not None else None),
                    "u_pnl": (str(bp.unrealized_pnl_gross) if bp.unrealized_pnl_gross is not None else None),
                    "leverage": (str(bp.leverage) if bp.leverage is not None else None),
                },
            )
    finally:
        await t.close()


if __name__ == "__main__":
    asyncio.run(main())
