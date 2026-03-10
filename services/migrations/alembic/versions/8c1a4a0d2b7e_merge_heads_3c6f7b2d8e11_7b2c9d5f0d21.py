"""merge heads 3c6f7b2d8e11 + 7b2c9d5f0d21

Revision ID: 8c1a4a0d2b7e
Revises: 3c6f7b2d8e11, 7b2c9d5f0d21
Create Date: 2026-03-09

This is a merge migration to resolve multiple heads.
No schema changes are performed here.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c1a4a0d2b7e"
down_revision: Union[str, Sequence[str], None] = ("3c6f7b2d8e11", "7b2c9d5f0d21")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merge only
    pass


def downgrade() -> None:
    # best-effort: cannot un-merge cleanly
    pass
