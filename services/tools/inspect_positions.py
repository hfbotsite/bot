from __future__ import annotations

import asyncio
import os

from services.bot_runtime.settings import BotSettings
from services.execution.transport_ccxt import CcxtAsyncTransport, TransportConfig


async def main() -> None:
    s = BotSettings.load_from_env()

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
        positions = await t.fetch_positions(symbols=["ETH/USDT:USDT"], params={})
        print("POSITIONS:")
        for p in positions:
            # CCXT normalized position object is dict-like
            print(p)
    finally:
        await t.close()


if __name__ == "__main__":
    asyncio.run(main())
