from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import get_session
from app.main import app


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_teams(client: TestClient) -> None:
    response = client.get("/teams")

    assert response.status_code == 200
    assert [team["code"] for team in response.json()] == ["LDN"]
