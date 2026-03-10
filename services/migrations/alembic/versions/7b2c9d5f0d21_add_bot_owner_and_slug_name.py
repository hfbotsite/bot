"""add_bot_owner_and_slug_name

Revision ID: 7b2c9d5f0d21
Revises: d1ea1ce7bcfd
Create Date: 2026-03-09

Adds:
- bots.created_by_user_id (who created the bot; UI ownership)
- bots.bot_name (unique slug-like name for strategy selection / UI)

Notes:
- We keep legacy columns:
  - bots.user_id (currently used by MVP scripts)
  - bots.name (human-readable)
- For existing rows we backfill:
  - created_by_user_id := user_id
  - bot_name := 'bot_' || left(id, 8)   (safe unique-ish); then enforce uniqueness.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b2c9d5f0d21"
down_revision: Union[str, Sequence[str], None] = "d1ea1ce7bcfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add nullable columns first (so upgrade works on existing data)
    op.add_column("bots", sa.Column("created_by_user_id", sa.String(length=36), nullable=True))
    op.add_column("bots", sa.Column("bot_name", sa.Text(), nullable=True))

    # 2) Backfill existing rows
    # created_by_user_id := user_id
    op.execute("UPDATE bots SET created_by_user_id = user_id WHERE created_by_user_id IS NULL")

    # bot_name := 'bot_' || left(id, 8) (lowercase) if missing
    # (Postgres: left(text, n))
    op.execute("UPDATE bots SET bot_name = lower('bot_' || left(id, 8)) WHERE bot_name IS NULL OR bot_name = ''")

    # 3) Constraints / indexes
    op.create_index("ix_bots_created_by_user_id", "bots", ["created_by_user_id"], unique=False)
    op.create_unique_constraint("uq_bots_bot_name", "bots", ["bot_name"])

    # 4) Make columns NOT NULL after backfill
    op.alter_column("bots", "created_by_user_id", existing_type=sa.String(length=36), nullable=False)
    op.alter_column("bots", "bot_name", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.drop_constraint("uq_bots_bot_name", "bots", type_="unique")
    op.drop_index("ix_bots_created_by_user_id", table_name="bots")
    op.drop_column("bots", "bot_name")
    op.drop_column("bots", "created_by_user_id")
