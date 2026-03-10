"""add_deals_exit_reason

Revision ID: 3c6f7b2d8e11
Revises: d1ea1ce7bcfd
Create Date: 2026-03-09 17:09:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c6f7b2d8e11"
down_revision: Union[str, Sequence[str], None] = "d1ea1ce7bcfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("exit_reason", sa.Text(), nullable=True))
    op.create_index("ix_deals_exit_reason", "deals", ["exit_reason"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_deals_exit_reason", table_name="deals")
    op.drop_column("deals", "exit_reason")
