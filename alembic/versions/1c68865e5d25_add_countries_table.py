"""add countries table

Revision ID: 1c68865e5d25
Revises: b56f4e83d1d8
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1c68865e5d25'
down_revision: Union[str, Sequence[str], None] = 'b56f4e83d1d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (fa_code, code, name)
COUNTRIES = [
    ("AUS", "AU", "Australia"),
    ("CAN", "CA", "Canada"),
    ("DEU", "DE", "Germany"),
    ("ESP", "ES", "Spain"),
    ("JPN", "JP", "Japan"),
    ("MEX", "MX", "Mexico"),
    ("NLD", "NL", "Netherlands"),
    ("NOR", "NO", "Norway"),
    ("SWE", "SE", "Sweden"),
    ("USA", "US", "United States of America"),
    ("ENG", "GB-ENG", "England"),
    ("SCO", "GB-SCT", "Scotland"),
    ("WAL", "GB-WLS", "Wales"),
]


countries_table = sa.table(
    "countries",
    sa.column("code", sqlmodel.sql.sqltypes.AutoString()),
    sa.column("fa_code", sqlmodel.sql.sqltypes.AutoString()),
    sa.column("name", sqlmodel.sql.sqltypes.AutoString()),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "countries",
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fa_code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index(op.f("ix_countries_fa_code"), "countries", ["fa_code"], unique=True)

    op.bulk_insert(
        countries_table,
        [{"fa_code": fa_code, "code": code, "name": name} for fa_code, code, name in COUNTRIES],
    )

    for fa_code, code, _name in COUNTRIES:
        op.execute(f"UPDATE players SET country = '{code}' WHERE country = '{fa_code}'")

    op.create_foreign_key(
        "fk_players_country_countries",
        "players",
        "countries",
        ["country"],
        ["code"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_players_country_countries", "players", type_="foreignkey")

    for fa_code, code, _name in COUNTRIES:
        op.execute(f"UPDATE players SET country = '{fa_code}' WHERE country = '{code}'")

    op.drop_index(op.f("ix_countries_fa_code"), table_name="countries")
    op.drop_table("countries")
