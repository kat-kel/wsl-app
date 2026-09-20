import pytest
from sqlmodel import Session, select

from app.models import Player
from app.schemas.player import PlayerCreate
from app.services import players as player_service
from app.services.errors import UnknownReference
from app.services.players import (
    normalize_name,
    player_exists,
    resolve_country_code,
    upsert_player,
    validate_references,
)


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [("US", "US"), ("USA", "US"), ("usa", "US"), ("ZZ", None)],
)
def test_resolve_country_code(
    session: Session, value: str, expected: str | None
) -> None:
    """Either spelling resolves to the stored ISO code; unknown codes resolve to None."""
    assert resolve_country_code(session, value) == expected


def test_player_exists_matches_the_normalized_form(session: Session) -> None:
    upsert_player(session, player())

    assert player_exists(session, "  ALEX   morgan ")
    assert not player_exists(session, "Sam Kerr")


def test_services_do_not_commit(session: Session) -> None:
    """The batch job's all-or-nothing guarantee rests on this: only callers commit."""
    upsert_player(session, player())
    session.rollback()

    assert session.exec(select(Player)).all() == []


def test_upsert_player_reports_created_then_updated(session: Session) -> None:
    """A second row with the same normalized name overwrites the first wholesale."""
    assert upsert_player(session, player()) is True
    assert upsert_player(session, player(full_name="alex  morgan", no=9)) is False

    found = session.exec(select(Player)).one()
    assert (found.full_name, found.no) == ("alex  morgan", 9)
    assert found.normalized_name == "alex morgan"


def test_upsert_player_still_validates_references(session: Session) -> None:
    with pytest.raises(UnknownReference, match="country_code"):
        upsert_player(session, player(country_code="ZZ"))


def test_upsert_player_survives_losing_the_race(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The losing run of two concurrent loads still has to write cleanly.

    It reads the natural key as free, another run inserts it, and then its own
    insert lands on the unique index. ON CONFLICT turns that collision into an
    update; the check-then-act version it replaced raised IntegrityError.
    """
    upsert_player(session, player())
    monkeypatch.setattr(player_service, "player_exists", lambda *_: False)

    assert upsert_player(session, player(no=9)) is True

    assert len(session.exec(select(Player)).all()) == 1
