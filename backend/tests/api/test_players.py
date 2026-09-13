from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.api.security import API_KEY_HEADER_NAME
from app.database import get_session
from app.main import app
from app.models import Country, Team

ALEX_MORGAN = {
    "full_name": "Alex Morgan",
    "shirt_name": "Morgan",
    "position": "Forward",
    "country_code": "US",
    "no": 13,
    "team_code": "LDN",
}

WRITE_ROUTES = [
    ("post", "/players"),
    ("put", "/players/1"),
    ("post", "/teams"),
    ("put", "/teams/1"),
]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Country(fa_code="USA", code="US", name="United States of America"))
        session.add(Team(code="LDN", full_name="London City", short_name="London"))
        session.commit()

        app.dependency_overrides[get_session] = lambda: session
        yield TestClient(app)
        app.dependency_overrides.clear()


def test_create_player(client: TestClient, write_headers: dict[str, str]) -> None:
    response = client.post("/players", json=ALEX_MORGAN, headers=write_headers)

    assert response.status_code == 201
    assert response.json() == {**ALEX_MORGAN, "id": 1, "normalized_name": "alex morgan"}


def test_create_player_without_team_or_number(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    player = {
        key: ALEX_MORGAN[key]
        for key in ("full_name", "shirt_name", "position", "country_code")
    }

    response = client.post("/players", json=player, headers=write_headers)

    assert response.status_code == 201
    assert response.json()["no"] is None
    assert response.json()["team_code"] is None


def test_create_player_rejects_duplicate_name(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    client.post("/players", json=ALEX_MORGAN, headers=write_headers)

    response = client.post(
        "/players",
        json={**ALEX_MORGAN, "full_name": "alex  morgan"},
        headers=write_headers,
    )

    assert response.status_code == 409


def test_get_players(client: TestClient, write_headers: dict[str, str]) -> None:
    client.post("/players", json=ALEX_MORGAN, headers=write_headers)

    response = client.get("/players")

    assert response.status_code == 200
    assert [player["full_name"] for player in response.json()] == ["Alex Morgan"]


def test_update_player(client: TestClient, write_headers: dict[str, str]) -> None:
    player_id = client.post("/players", json=ALEX_MORGAN, headers=write_headers).json()[
        "id"
    ]

    response = client.put(
        f"/players/{player_id}",
        json={**ALEX_MORGAN, "position": "Midfielder", "no": 7},
        headers=write_headers,
    )

    assert response.status_code == 200
    assert response.json()["position"] == "Midfielder"
    assert response.json()["no"] == 7


def test_update_unknown_player(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    response = client.put("/players/404", json=ALEX_MORGAN, headers=write_headers)

    assert response.status_code == 404


def test_create_player_rejects_unknown_country(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    response = client.post(
        "/players", json={**ALEX_MORGAN, "country_code": "ZZ"}, headers=write_headers
    )

    assert response.status_code == 422
    assert "country_code" in response.json()["detail"]


def test_create_player_rejects_unknown_team(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    response = client.post(
        "/players", json={**ALEX_MORGAN, "team_code": "NOPE"}, headers=write_headers
    )

    assert response.status_code == 422
    assert "team_code" in response.json()["detail"]


def test_update_player_rejects_unknown_country(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    player_id = client.post("/players", json=ALEX_MORGAN, headers=write_headers).json()[
        "id"
    ]

    response = client.put(
        f"/players/{player_id}",
        json={**ALEX_MORGAN, "country_code": "ZZ"},
        headers=write_headers,
    )

    assert response.status_code == 422


def test_create_player_rejects_oversized_name(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    response = client.post(
        "/players", json={**ALEX_MORGAN, "full_name": "A" * 200}, headers=write_headers
    )

    assert response.status_code == 422


def test_create_player_rejects_blank_name(
    client: TestClient, write_headers: dict[str, str]
) -> None:
    response = client.post(
        "/players", json={**ALEX_MORGAN, "full_name": "   "}, headers=write_headers
    )

    assert response.status_code == 422


@pytest.mark.parametrize(("method", "path"), WRITE_ROUTES)
def test_write_routes_reject_missing_api_key(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path, json=ALEX_MORGAN)

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), WRITE_ROUTES)
def test_write_routes_reject_wrong_api_key(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(
        method, path, json=ALEX_MORGAN, headers={API_KEY_HEADER_NAME: "wrong-key"}
    )

    assert response.status_code == 401


SQUAD = [
    # (full_name, shirt_name, position, no)
    ("Ella Toone", "Toone", "midfielder", 7),
    ("Janina Leitzig", "Leitzig", "goalkeeper", 25),
    ("Dominique Janssen", "Janssen", "defender", 17),
    ("Elisabeth Terland", "Terland", "forward", 10),
    ("Anna Sandberg", "Sandberg", "defender", 2),
]


@pytest.fixture()
def squad(client: TestClient, write_headers: dict[str, str]) -> TestClient:
    for full_name, shirt_name, position, no in SQUAD:
        client.post(
            "/players",
            json={
                "full_name": full_name,
                "shirt_name": shirt_name,
                "position": position,
                "country_code": "US",
                "no": no,
            },
            headers=write_headers,
        )
    return client


def shirt_names(response) -> list[str]:
    return [player["shirt_name"] for player in response.json()]


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


def test_players_reject_unknown_sort(squad: TestClient) -> None:
    assert squad.get("/players?sort=nonsense").status_code == 422


def test_any_configured_key_is_accepted(
    client: TestClient, all_write_api_keys: list[str]
) -> None:
    """Every configured key works at once, which is what makes rotation seamless."""
    assert len(all_write_api_keys) > 1

    for index, key in enumerate(all_write_api_keys):
        response = client.post(
            "/players",
            json={**ALEX_MORGAN, "full_name": f"Player {index}"},
            headers={API_KEY_HEADER_NAME: key},
        )

        assert response.status_code == 201


def test_read_routes_do_not_require_api_key(client: TestClient) -> None:
    assert client.get("/players").status_code == 200
    assert client.get("/teams").status_code == 200
    assert client.get("/countries").status_code == 200
