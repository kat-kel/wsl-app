"""Populate a database from CSV files via the API's write endpoints.

Usage (from the backend/ directory, with the API running):

    uv run python scripts/load_csv.py teams
    uv run python scripts/load_csv.py players
    uv run python scripts/load_csv.py players -i other.csv

Each subcommand defaults to its file in scripts/data/; -i/--infile overrides it.

WRITE_API_KEY comes from backend/.env and must be one of the keys the API accepts
(its WRITE_API_KEYS). An exported WRITE_API_KEY wins over the file, so targeting a
deployed environment is a matter of setting it alongside WSL_API_BASE:

    WSL_API_BASE=https://... WRITE_API_KEY=<key> uv run python scripts/load_csv.py teams

Rows are matched to existing records by a natural key (team code, normalized
player name), so re-running updates rather than duplicates.

teams.csv columns:   code, full_name, short_name
players.csv columns: full_name, shirt_name, position, country, no, team_code
                     (country accepts either an ISO code like US or an FA code
                     like USA; no and team_code may be left blank)
"""

import csv
import os
from pathlib import Path
from typing import Any

import click
import httpx2
from dotenv import load_dotenv

# Pinned to backend/.env: bare load_dotenv() walks up the tree and would fall
# back to the repo-root .env if this file were ever missing.
load_dotenv(Path(__file__).parents[1] / ".env")

API_BASE = os.environ.get("WSL_API_BASE", "http://localhost:8000")
API_KEY_HEADER_NAME = "X-API-Key"

PLAYERS_CSV = Path(__file__).parent.joinpath("data", "players.csv")
TEAMS_CSV = Path(__file__).parent.joinpath("data", "teams.csv")

# path_type makes click hand the callback a Path; without it every command
# receives a plain str and read_csv's path.open() fails.
CSV_PATH = click.Path(exists=True, dir_okay=False, path_type=Path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [
            {
                key: (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            for row in csv.DictReader(file)
        ]


def blank_to_none(value: str) -> str | None:
    return value or None


def normalize_name(full_name: str) -> str:
    return " ".join(full_name.casefold().split())


def upsert(
    client: httpx2.Client,
    path: str,
    payload: dict[str, Any],
    existing_id: int | None,
) -> str:
    if existing_id is None:
        response = client.post(path, json=payload)
        action = "created"
    else:
        response = client.put(f"{path}/{existing_id}", json=payload)
        action = "updated"

    if response.is_error:
        return f"failed ({response.status_code}: {response.text})"
    return action


def load_teams(client: httpx2.Client, infile: Path) -> None:
    ids_by_code = {team["code"]: team["id"] for team in client.get("/teams").json()}

    for row in read_csv(infile):
        payload = {
            "code": row["code"],
            "full_name": row["full_name"],
            "short_name": row["short_name"],
        }
        result = upsert(client, "/teams", payload, ids_by_code.get(row["code"]))
        print(f"team {row['code']}: {result}")


def load_players(client: httpx2.Client, infile: Path) -> None:
    countries = client.get("/countries").json()
    country_codes = {country["code"]: country["code"] for country in countries}
    country_codes |= {country["fa_code"]: country["code"] for country in countries}

    ids_by_name = {
        player["normalized_name"]: player["id"]
        for player in client.get("/players").json()
    }

    for line, row in enumerate(read_csv(infile), start=2):
        label = row.get("full_name") or f"line {line}"

        missing = [
            column
            for column in ("full_name", "shirt_name", "position", "country")
            if not row.get(column)
        ]
        if missing:
            print(f"player {label}: skipped, missing {', '.join(missing)}")
            continue

        country_code = country_codes.get(row["country"].upper())
        if country_code is None:
            print(f"player {label}: skipped, unknown country {row['country']!r}")
            continue

        number = row.get("no", "")
        if number and not number.isdigit():
            print(f"player {label}: skipped, non-numeric squad number {number!r}")
            continue

        payload = {
            "full_name": row["full_name"],
            "shirt_name": row["shirt_name"],
            "position": row["position"],
            "country_code": country_code,
            "no": int(number) if number else None,
            "team_code": blank_to_none(row.get("team_code", "")),
        }
        existing_id = ids_by_name.get(normalize_name(row["full_name"]))
        result = upsert(client, "/players", payload, existing_id)
        print(f"player {row['full_name']}: {result}")


class Conf:
    def __init__(self) -> None:
        key = os.environ.get("WRITE_API_KEY")
        if not key:
            raise click.ClickException(
                "WRITE_API_KEY is not set; write endpoints will reject every request."
            )
        self.key = key

    def client(self) -> httpx2.Client:
        return httpx2.Client(
            base_url=API_BASE, timeout=30, headers={API_KEY_HEADER_NAME: self.key}
        )


# ensure=True builds Conf only when a subcommand runs, so --help works without a key.
pass_conf = click.make_pass_decorator(Conf, ensure=True)


@click.group()
def cli() -> None:
    """CREATE or UPDATE rows in the Postgres database via the API."""


@cli.command()
@click.option("-i", "--infile", type=CSV_PATH, default=PLAYERS_CSV, show_default=True)
@pass_conf
def players(conf: Conf, infile: Path) -> None:
    """Load players from a CSV."""
    with conf.client() as client:
        load_players(client, infile)


@cli.command()
@click.option("-i", "--infile", type=CSV_PATH, default=TEAMS_CSV, show_default=True)
@pass_conf
def teams(conf: Conf, infile: Path) -> None:
    """Load teams from a CSV."""
    with conf.client() as client:
        load_teams(client, infile)


if __name__ == "__main__":
    cli()
