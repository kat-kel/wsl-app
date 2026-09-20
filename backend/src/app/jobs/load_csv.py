"""Load teams and players into the database from CSV files.

This runs as a batch job, not through the API. It opens its own database session
and writes through the service layer, so validation and the natural-key rules
live in one place, and it needs no API key -- only DATABASE_URL and DATA_SOURCE.

Locally, run it inside the backend container, which is also how it runs in
production:

    just db-load teams
    just db-load players

Where the CSV comes from is configuration, not code: DATA_SOURCE points at the
local fixtures directory in development and at a GCS bucket in a deployed
environment. See sources.py.

A run is all or nothing. Every row is validated first, and if any row is bad
nothing at all is written. A squad list is a coherent set, so a half-applied
load is worse than none, and it means re-running after a fix is always safe.

Rows are matched to existing records by a natural key -- team code, and the
player's normalized name -- so re-running updates rather than duplicating. The
match and the write are a single ON CONFLICT statement, so two runs overlapping
cannot collide on the unique index.

teams.csv columns:   code, full_name, short_name
players.csv columns: full_name, shirt_name, position, country, no, team_code
                     (country accepts either an ISO code like US or an FA code
                     like USA; no and team_code may be left blank)
"""

import csv
from collections.abc import Callable
from dataclasses import dataclass

import click
from pydantic import BaseModel, ValidationError
from sqlmodel import Session, create_engine

from app.config import get_database_settings
from app.jobs.sources import Source, resolve
from app.schemas.player import PlayerCreate
from app.schemas.team import TeamCreate
from app.services import players as player_service
from app.services import teams as team_service
from app.services.errors import UnknownReference

SOURCE_HELP = "URI of the CSV to load. Defaults to <DATA_SOURCE>/<name>.csv."

# Its own engine, built from the write-capable DatabaseSettings, rather than
# importing the API's -- app.database connects with a role that can only
# SELECT, which would make every load fail on its first insert.
engine = create_engine(get_database_settings().database_url, pool_pre_ping=True)


@dataclass(frozen=True)
class RowError:
    """A problem with one CSV row, carried with its line number for reporting."""

    line: int
    message: str


type Row = tuple[int, dict[str, str]]
type Parsed[T] = tuple[list[T], list[RowError]]


def read_csv(source: Source) -> list[Row]:
    """Rows paired with their line number in the file, so errors can point at one.

    The None key holds any columns beyond the header, which are dropped.
    """
    with source.open() as file:
        return [
            (
                line,
                {
                    key: (value or "").strip()
                    for key, value in row.items()
                    if key is not None
                },
            )
            for line, row in enumerate(csv.DictReader(file), start=2)
        ]


def describe(error: ValidationError) -> str:
    """Flatten a Pydantic error into one line naming each offending field."""
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    )


def parse_teams(session: Session, rows: list[Row]) -> Parsed[TeamCreate]:
    """Validate every team row. The session is unused but keeps the run() shape."""
    del session

    parsed: list[TeamCreate] = []
    errors: list[RowError] = []

    for line, row in rows:
        try:
            parsed.append(
                TeamCreate(
                    code=row.get("code", ""),
                    full_name=row.get("full_name", ""),
                    short_name=row.get("short_name", ""),
                )
            )
        except ValidationError as error:
            errors.append(RowError(line, describe(error)))

    return parsed, errors


def parse_players(session: Session, rows: list[Row]) -> Parsed[PlayerCreate]:
    """Validate every player row, resolving country and team codes as it goes.

    References are checked here rather than left to the service layer so that a
    bad code is reported with its line number alongside every other problem,
    before anything is written.
    """
    parsed: list[PlayerCreate] = []
    errors: list[RowError] = []

    for line, row in rows:
        country = row.get("country", "")
        if not country:
            errors.append(RowError(line, "country: missing"))
            continue

        country_code = player_service.resolve_country_code(session, country)
        if country_code is None:
            errors.append(RowError(line, f"country: unknown code {country!r}"))
            continue

        number = row.get("no", "")
        if number and not number.isdigit():
            errors.append(RowError(line, f"no: non-numeric squad number {number!r}"))
            continue

        team_code = row.get("team_code") or None
        if team_code and team_service.find_team_by_code(session, team_code) is None:
            errors.append(RowError(line, f"team_code: unknown code {team_code!r}"))
            continue

        try:
            parsed.append(
                PlayerCreate(
                    full_name=row.get("full_name", ""),
                    shirt_name=row.get("shirt_name", ""),
                    position=row.get("position", ""),
                    country_code=country_code,
                    no=int(number) if number else None,
                    team_code=team_code,
                )
            )
        except ValidationError as error:
            errors.append(RowError(line, describe(error)))

    return parsed, errors


def apply_teams(session: Session, parsed: list[TeamCreate]) -> tuple[int, int]:
    created = updated = 0

    for team_data in parsed:
        if team_service.upsert_team(session, team_data):
            created += 1
        else:
            updated += 1

    return created, updated


def apply_players(session: Session, parsed: list[PlayerCreate]) -> tuple[int, int]:
    created = updated = 0

    # Each row is resolved against the live session rather than a map built up
    # front, so two rows sharing a name in one file update each other instead of
    # colliding on the unique index.
    for player_data in parsed:
        if player_service.upsert_player(session, player_data):
            created += 1
        else:
            updated += 1

    return created, updated


def run[T: BaseModel](
    source: Source,
    label: str,
    parse: Callable[[Session, list[Row]], Parsed[T]],
    apply: Callable[[Session, list[T]], tuple[int, int]],
) -> None:
    """Validate the whole file, then apply it in a single transaction."""
    rows = read_csv(source)

    with Session(engine) as session:
        parsed, errors = parse(session, rows)

        if errors:
            for error in errors:
                click.echo(f"{source.name}:{error.line}: {error.message}", err=True)
            raise click.ClickException(
                f"{len(errors)} invalid row(s) of {len(rows)}; nothing was written."
            )

        try:
            created, updated = apply(session, parsed)
            session.commit()
        except UnknownReference as error:
            session.rollback()
            raise click.ClickException(f"{error}; nothing was written.") from error

    click.echo(f"{label}: created {created}, updated {updated}")


@click.group()
def cli() -> None:
    """Create or update rows in the database from CSV files."""


@cli.command()
@click.option("-s", "--source", "uri", default=None, help=SOURCE_HELP)
def players(uri: str | None) -> None:
    """Load players from a CSV."""
    run(resolve("players", uri), "players", parse_players, apply_players)


@cli.command()
@click.option("-s", "--source", "uri", default=None, help=SOURCE_HELP)
def teams(uri: str | None) -> None:
    """Load teams from a CSV."""
    run(resolve("teams", uri), "teams", parse_teams, apply_teams)


if __name__ == "__main__":
    cli()
