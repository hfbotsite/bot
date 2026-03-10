from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass
from typing import Optional

from .runtime import BotRuntime
from .settings import BotSettings


@dataclass(frozen=True, slots=True)
class ExitSignals:
    sigint: bool = False
    sigterm: bool = False


async def _amain() -> int:
    # Load .env (if present) for local/dev runs. In containers, env is injected by orchestrator.
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(override=False)
    except Exception:
        pass

    settings = BotSettings.load_from_env()

    bot_mode = (os.environ.get("BOT_MODE") or "runtime").lower()

    if bot_mode == "smoke":
        from .smoke_trading import run_smoke_trading

        await run_smoke_trading(settings=settings)
        return 0

    runtime = BotRuntime(settings=settings)

    # Graceful shutdown
    stop_event = asyncio.Event()

    def _request_stop(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, _request_stop)
        loop.add_signal_handler(signal.SIGTERM, _request_stop)
    except NotImplementedError:
        # Windows fallback or limited environments.
        signal.signal(signal.SIGINT, lambda *_: _request_stop())
        signal.signal(signal.SIGTERM, lambda *_: _request_stop())

    await runtime.start()
    await stop_event.wait()
    await runtime.stop()
    return 0


def main() -> None:
    # Ensure deterministic asyncio policy on Windows if needed
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
        except Exception:
            pass

    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
