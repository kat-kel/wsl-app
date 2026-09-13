"""add teams table and player squad fields

Revision ID: 3a7d92f4c118
Revises: 1c68865e5d25
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '3a7d92f4c118'
down_revision: Union[str, Sequence[str], None] = '1c68865e5d25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("short_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_code"), "teams", ["code"], unique=True)

    op.alter_column("players", "country", new_column_name="country_code")
    op.execute("ALTER INDEX ix_players_country RENAME TO ix_players_country_code")

    op.add_column("players", sa.Column("no", sa.Integer(), nullable=True))
    op.add_column(
        "players",
        sa.Column("team_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(op.f("ix_players_team_code"), "players", ["team_code"], unique=False)
    op.create_foreign_key(
        "fk_players_team_code_teams", "players", "teams", ["team_code"], ["code"]
    )

    op.create_index(
        op.f("ix_players_normalized_name"), "players", ["normalized_name"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_players_normalized_name"), table_name="players")

    op.drop_constraint("fk_players_team_code_teams", "players", type_="foreignkey")
    op.drop_index(op.f("ix_players_team_code"), table_name="players")
    op.drop_column("players", "team_code")
    op.drop_column("players", "no")

    op.execute("ALTER INDEX ix_players_country_code RENAME TO ix_players_country")
    op.alter_column("players", "country_code", new_column_name="country")

    op.drop_index(op.f("ix_teams_code"), table_name="teams")
    op.drop_table("teams")
