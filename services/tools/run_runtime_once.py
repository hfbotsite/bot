from __future__ import annotations

import asyncio

from services.bot_runtime.runtime import BotRuntime
from services.bot_runtime.settings import BotSettings


async def main() -> None:
    s = BotSettings.load_from_env()
    r = BotRuntime(settings=s)
    try:
        await r.start()
        await asyncio.sleep(2)
    finally:
        await r.stop()


if __name__ == "__main__":
    asyncio.run(main())
