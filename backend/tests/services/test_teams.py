import pytest
from sqlmodel import Session, select

from app.models import Team
from app.schemas.team import TeamCreate
from app.services import teams as team_service
from app.services.teams import find_team_by_code, upsert_team


def team(**overrides: object) -> TeamCreate:
    return TeamCreate(
        **{
            "code": "MUN",
            "full_name": "Manchester United Women's FC",
            "short_name": "Manchester United",
            **overrides,
        }
    )


def test_upsert_team_assigns_an_id(session: Session) -> None:
    upsert_team(session, team())

    created = find_team_by_code(session, "MUN")
    assert created is not None
    assert created.id is not None


def test_find_team_by_code(session: Session) -> None:
    assert find_team_by_code(session, "LDN") is not None
    assert find_team_by_code(session, "NOPE") is None


def test_upsert_team_copies_every_field(session: Session) -> None:
    """The seeded LDN team is overwritten wholesale, not merged field by field."""
    upsert_team(session, team(code="LDN", short_name="London Town"))

    updated = find_team_by_code(session, "LDN")
    assert updated is not None
    assert updated.short_name == "London Town"
    assert updated.full_name == "Manchester United Women's FC"


def test_services_do_not_commit(session: Session) -> None:
    upsert_team(session, team())
    session.rollback()

    assert [found.code for found in session.exec(select(Team)).all()] == ["LDN"]


def test_upsert_team_reports_created_then_updated(session: Session) -> None:
    assert upsert_team(session, team()) is True
    assert upsert_team(session, team(short_name="Man United")) is False

    found = find_team_by_code(session, "MUN")
    assert found is not None
    assert found.short_name == "Man United"


def test_upsert_team_survives_losing_the_race(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The losing run of two concurrent loads still has to write cleanly.

    It reads the natural key as free, another run inserts it, and then its own
    insert lands on the unique index. ON CONFLICT turns that collision into an
    update; the check-then-act version it replaced raised IntegrityError.
    """
    upsert_team(session, team())
    monkeypatch.setattr(team_service, "team_exists", lambda *_: False)

    assert upsert_team(session, team(short_name="Man United")) is True

    assert [found.code for found in session.exec(select(Team)).all()] == ["LDN", "MUN"]
