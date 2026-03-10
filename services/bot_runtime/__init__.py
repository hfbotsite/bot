"""Container entrypoint runtime for a single trading bot.

This package is intended to be run as:

    python -m services.bot_runtime

It wires together:
- market data (WS candles)
- indicators + strategy engine
- execution (ccxt via services.execution)
- persistence (PostgreSQL via services.bot_engine repos)
"""
