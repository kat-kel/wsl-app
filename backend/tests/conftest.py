from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.models import Country, Team


@pytest.fixture()
def engine() -> Iterator[Engine]:
    """An empty schema seeded with the reference rows the tests write against.

    StaticPool keeps every connection the same in-memory database, so a fresh
    Session opened later -- as the load job does -- still sees this data.
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Country(fa_code="USA", code="US", name="United States of America"))
        session.add(Team(code="LDN", full_name="London City", short_name="London"))
        session.commit()

    yield engine


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
