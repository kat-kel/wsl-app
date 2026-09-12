from collections.abc import Iterator
from csv import writer
from io import StringIO

import pytest
from sqlmodel import Session, SQLModel, StaticPool, create_engine, select

from app.models import Player
from app.schemas.player import PlayerImportResult
from app.services.players import import_players_from_csv

TWO_PLAYERS = [
    ("Alex Morgan", "Forward", "USA"),
    ("Sam Kerr", "Forward", "Australia"),
]

DUPLICATE_PLAYERS = [
    ("Alex Morgan", "Forward", "USA"),
    ("Sam Kerr", "Forward", "Australia"),
    ("Alex Morgan", "Forward", "USA"),
]


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_csv_file(rows: list[tuple]) -> StringIO:
    csv_file = StringIO()
    csv_writer = writer(csv_file)
    csv_writer.writerow(["name", "position", "country"])
    csv_writer.writerows(rows)
    csv_file.seek(0)
    return csv_file


@pytest.mark.parametrize(
    ("rows"),
    [
        TWO_PLAYERS,
        DUPLICATE_PLAYERS,
    ],
)
def test_import_two_players_from_csv(session: Session, rows: list[tuple]) -> None:
    result: PlayerImportResult = import_players_from_csv(make_csv_file(rows), session)

    players = session.exec(select(Player)).all()
    player_names = {player.display_name for player in players}

    assert result.total_rows == len(rows)
    assert result.created == 2
    assert result.updated == 0
    assert result.already_existing == 0
    assert result.duplicates_in_file == len(rows) - 2
    assert result.errors == []
    assert len(players) == 2
    assert player_names == {"Alex Morgan", "Sam Kerr"}


def test_import_players_from_csv_with_missing_columns(session: Session) -> None:
    csv_file = StringIO()
    csv_file.write("name,position\n")
    csv_file.write("Alex Morgan,Forward\n")
    csv_file.seek(0)

    result = import_players_from_csv(csv_file, session)

    assert result.total_rows == 0
    assert result.created == 0
    assert result.updated == 0
    assert result.already_existing == 0
    assert result.duplicates_in_file == 0
    assert "country" in result.errors


def test_import_players_skips_existing_players(session: Session) -> None:
    existing_player = Player(
        display_name="Alex Morgan",
        normalized_name="alex morgan",
        position="Forward",
        country="USA",
    )
    session.add(existing_player)
    session.commit()
    _players = session.exec(select(Player)).all()
    assert len(_players) == 1

    result = import_players_from_csv(make_csv_file(TWO_PLAYERS), session)

    players = session.exec(select(Player)).all()
    player_names = {player.display_name for player in players}

    assert result.total_rows == len(TWO_PLAYERS)
    assert result.created == 1  # Only Sam Kerr should be created
    assert result.updated == 0
    assert result.already_existing == 1  # Alex Morgan already exists
    assert result.duplicates_in_file == 0
    assert result.errors == []
    assert len(players) == 2
    assert player_names == {"Alex Morgan", "Sam Kerr"}
