from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.models import Country, Team
from app.schemas.player import PlayerCreate
from app.services.players import UnknownReference, normalize_name, validate_references


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Country(fa_code="USA", code="US", name="United States of America"))
        session.add(Team(code="LDN", full_name="London City", short_name="London"))
        session.commit()
        yield session


def player(**overrides: object) -> PlayerCreate:
    return PlayerCreate(
        **{
            "full_name": "Alex Morgan",
            "shirt_name": "Morgan",
            "position": "forward",
            "country_code": "US",
            **overrides,
        }
    )


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Alex Morgan", "alex morgan"),
        ("  Alex   MORGAN ", "alex morgan"),
        ("SAM KERR", "sam kerr"),
    ],
)
def test_normalize_name(full_name: str, expected: str) -> None:
    assert normalize_name(full_name) == expected


def test_validate_references_accepts_known_codes(session: Session) -> None:
    validate_references(player(team_code="LDN"), session)


def test_validate_references_allows_a_player_with_no_team(session: Session) -> None:
    validate_references(player(team_code=None), session)


def test_validate_references_rejects_unknown_country(session: Session) -> None:
    with pytest.raises(UnknownReference, match="country_code"):
        validate_references(player(country_code="ZZ"), session)


def test_validate_references_rejects_unknown_team(session: Session) -> None:
    with pytest.raises(UnknownReference, match="team_code"):
        validate_references(player(team_code="NOPE"), session)
