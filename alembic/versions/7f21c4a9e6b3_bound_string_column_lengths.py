"""bound string column lengths

Revision ID: 7f21c4a9e6b3
Revises: 3a7d92f4c118
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f21c4a9e6b3'
down_revision: Union[str, Sequence[str], None] = '3a7d92f4c118'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, length, nullable)
BOUNDED_COLUMNS = [
    ("countries", "code", 8, False),
    ("countries", "fa_code", 3, False),
    ("countries", "name", 100, False),
    ("teams", "code", 8, False),
    ("teams", "full_name", 100, False),
    ("teams", "short_name", 60, False),
    ("players", "full_name", 120, False),
    ("players", "normalized_name", 120, False),
    ("players", "shirt_name", 60, False),
    ("players", "country_code", 8, False),
    ("players", "position", 30, False),
    ("players", "team_code", 8, True),
]


def upgrade() -> None:
    """Upgrade schema."""
    for table, column, length, nullable in BOUNDED_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.VARCHAR(),
            type_=sa.String(length=length),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table, column, length, nullable in BOUNDED_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=length),
            type_=sa.VARCHAR(),
            existing_nullable=nullable,
        )
