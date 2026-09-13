"""player - add shirt name

Revision ID: b56f4e83d1d8
Revises: 45d87296611c
Create Date: 2026-09-13 09:12:56.712015

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b56f4e83d1d8"
down_revision: str | Sequence[str] | None = "45d87296611c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add columns as nullable first
    op.add_column("players", sa.Column("full_name", sa.String(), nullable=True))
    op.add_column("players", sa.Column("shirt_name", sa.String(), nullable=True))

    # 2. Backfill from existing data
    op.execute("UPDATE players SET full_name = display_name")
    op.execute("UPDATE players SET shirt_name = display_name")

    # 3. Now enforce NOT NULL
    op.alter_column("players", "full_name", nullable=False)
    op.alter_column("players", "shirt_name", nullable=False)

    # 4. Drop the old column
    op.drop_column("players", "display_name")

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Add display_name back as nullable first
    op.add_column("players", sa.Column("display_name", sa.VARCHAR(), nullable=True))

    # 2. Backfill from full_name
    op.execute("UPDATE players SET display_name = full_name")

    # 3. Now enforce NOT NULL
    op.alter_column("players", "display_name", nullable=False)

    # 4. Drop the new columns
    op.drop_column("players", "shirt_name")
    op.drop_column("players", "full_name")
