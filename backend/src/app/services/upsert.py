"""Atomic create-or-update keyed on a natural key.

Reading a row and then choosing to insert or update is check-then-act: two
concurrent load jobs can both find nothing, both insert, and one loses to the
unique index. `INSERT ... ON CONFLICT DO UPDATE` collapses the pair into a
single statement the database settles atomically, so the racing run updates the
winner's row instead of failing on it.

Postgres and SQLite both implement ON CONFLICT, but each exposes it through its
own dialect construct, so the statement is built for whichever the session is
bound to -- Postgres in every deployment, SQLite under the unit tests.
"""

from typing import Any

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, SQLModel

INSERTS = {"postgresql": postgresql_insert, "sqlite": sqlite_insert}


def upsert(
    session: Session, model: type[SQLModel], values: dict[str, Any], key: str
) -> None:
    """Insert values, or overwrite whichever row already holds this natural key.

    The key column is left out of the update: it is what the two rows have in
    common, so writing it back would be a no-op. The caller owns the
    transaction and commits.
    """
    insert = INSERTS[session.get_bind().dialect.name]

    session.execute(
        insert(model)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[key],
            set_={name: value for name, value in values.items() if name != key},
        )
    )
