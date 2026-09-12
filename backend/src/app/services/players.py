import csv
from typing import TextIO

from pydantic import ValidationError
from sqlmodel import Session, select

from app.models import Player
from app.schemas.player import PlayerImportRead, PlayerImportResult
from app.services.errors import MissingColumns


def import_players_from_csv(
    file: TextIO,
    session: Session,
) -> PlayerImportResult:

    reader = csv.DictReader(file)
    required_columns = {"name", "position", "country"}
    actual_columns = set(reader.fieldnames or [])
    missing_columns = required_columns - actual_columns
    if missing_columns:
        return PlayerImportResult(
            total_rows=0,
            created=0,
            updated=0,
            already_existing=0,
            duplicates_in_file=0,
            errors=[str(MissingColumns(col)) for col in missing_columns],
        )

    rows = list(reader)
    total_rows = len(rows)
    errors: list[str] = []
    candidates: dict[str, Player] = {}
    duplicates_in_file = 0

    for row_numer, row in enumerate(rows, start=2):
        try:
            imported_player = PlayerImportRead.model_validate(row)
        except ValidationError as e:
            errors.append(f"Row {row_numer}: {e}")
            continue

        if imported_player.normalized_name in candidates:
            duplicates_in_file += 1
            continue

        candidates[imported_player.normalized_name] = Player(
            display_name=imported_player.name,
            normalized_name=imported_player.normalized_name,
            position=imported_player.position,
            country=imported_player.country,
        )

    if not candidates:
        return PlayerImportResult(
            total_rows=total_rows,
            created=0,
            updated=0,
            already_existing=0,
            duplicates_in_file=duplicates_in_file,
            errors=errors,
        )

    existing_names = set(
        session.exec(
            select(Player.normalized_name).where(
                Player.normalized_name.in_(candidates.keys())
            )
        ).all()
    )

    new_players = [
        player for name, player in candidates.items() if name not in existing_names
    ]

    session.add_all(new_players)
    session.commit()

    return PlayerImportResult(
        total_rows=total_rows,
        created=len(new_players),
        updated=0,
        already_existing=len(existing_names),
        duplicates_in_file=duplicates_in_file,
        errors=errors,
    )
