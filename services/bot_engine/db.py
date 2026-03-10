from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine


def get_database_url() -> str:
    """Return database URL for engine.

    Priority:
    - BOT_DB_URL env var
    - DATABASE_URL env var
    - fallback to local dev DSN (matches services/migrations/alembic.ini)
    """

    bot_db_url = os.getenv("BOT_DB_URL")
    if bot_db_url:
        bot_db_url = bot_db_url.strip()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        database_url = database_url.strip()

    return bot_db_url or database_url or "postgresql+psycopg://bot:bot@localhost:5433/bot_platform"


def create_db_engine(url: str | None = None) -> Engine:
    """Create sync SQLAlchemy Engine (MVP).

    Engine is used by bot engine for direct SQLAlchemy Core operations.
    We keep it sync for MVP to simplify deterministic sequential PnL updates.
    """

    return create_engine(url or get_database_url(), future=True, pool_pre_ping=True)
