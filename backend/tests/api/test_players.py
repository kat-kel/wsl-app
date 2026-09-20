from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import get_session
from app.main import app
from app.schemas.player import PlayerCreate
from app.services.players import upsert_player

SQUAD = [
    # (full_name, shirt_name, position, no)
    ("Ella Toone", "Toone", "midfielder", 7),
    ("Janina Leitzig", "Leitzig", "goalkeeper", 25),
    ("Dominique Janssen", "Janssen", "defender", 17),
    ("Elisabeth Terland", "Terland", "forward", 10),
    ("Anna Sandberg", "Sandberg", "defender", 2),
]


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def squad(client: TestClient, session: Session) -> TestClient:
    """Seeded through the service layer, the way the load job seeds it.

    The API has no write endpoints to seed through any more, which is the point:
    these tests exercise the read surface that is actually deployed.
    """
    for full_name, shirt_name, position, no in SQUAD:
        upsert_player(
            session,
            PlayerCreate(
                full_name=full_name,
                shirt_name=shirt_name,
                position=position,
                country_code="US",
                no=no,
            ),
        )
    session.commit()
    return client


def shirt_names(response) -> list[str]:
    return [player["shirt_name"] for player in response.json()]


def test_get_players(squad: TestClient) -> None:
    response = squad.get("/players")

    assert response.status_code == 200
    assert len(response.json()) == len(SQUAD)


def test_get_players_is_empty_without_data(client: TestClient) -> None:
    assert client.get("/players").json() == []


def test_player_fields(squad: TestClient) -> None:
    toone = next(player for player in squad.get("/players").json() if player["no"] == 7)

    assert toone["full_name"] == "Ella Toone"
    assert toone["normalized_name"] == "ella toone"
    assert toone["country_code"] == "US"
    assert toone["team_code"] is None


def test_players_sort_by_name_by_default(squad: TestClient) -> None:
    assert shirt_names(squad.get("/players")) == [
        "Janssen",
        "Leitzig",
        "Sandberg",
        "Terland",
        "Toone",
    ]


def test_players_sort_by_number(squad: TestClient) -> None:
    assert shirt_names(squad.get("/players?sort=number")) == [
        "Sandberg",
        "Toone",
        "Terland",
        "Janssen",
        "Leitzig",
    ]


def test_players_sort_by_position_in_footballing_order(squad: TestClient) -> None:
    positions = [
        player["position"] for player in squad.get("/players?sort=position").json()
    ]

    assert positions == [
        "goalkeeper",
        "defender",
        "defender",
        "midfielder",
        "forward",
    ]


def test_players_sort_by_position_then_number(squad: TestClient) -> None:
    assert shirt_names(squad.get("/players?sort=position")) == [
        "Leitzig",
        "Sandberg",
        "Janssen",
        "Toone",
        "Terland",
    ]


def test_players_sort_by_position_then_name(squad: TestClient) -> None:
    assert shirt_names(squad.get("/players?sort=position_name")) == [
        "Leitzig",
        "Janssen",
        "Sandberg",
        "Toone",
        "Terland",
    ]


def test_players_reject_unknown_sort(client: TestClient) -> None:
    assert client.get("/players?sort=nope").status_code == 422
