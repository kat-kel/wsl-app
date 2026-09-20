import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner, Result
from sqlalchemy import Engine
from sqlmodel import Session, select

import app
from app.jobs import load_csv
from app.jobs.sources import Source
from app.models import Player, Team

PLAYERS_HEADER = "full_name,shirt_name,position,country,no,team_code\n"
TEAMS_HEADER = "code,full_name,short_name\n"

MORGAN = "Alex Morgan,Morgan,forward,USA,13,LDN\n"
KERR = "Sam Kerr,Kerr,forward,US,20,\n"


def write_csv(tmp_path: Path, name: str, body: str) -> Path:
    """Test CSVs are written per test, never committed.

    The repo ignores stray *.csv outside fixtures/, so a checked-in file here
    would exist on the author's machine and be silently missing in CI.
    """
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def source(path: Path) -> Source:
    return Source(str(path))


def player_row(**overrides: str) -> dict[str, str]:
    return {
        "full_name": "Alex Morgan",
        "shirt_name": "Morgan",
        "position": "forward",
        "country": "USA",
        "no": "13",
        "team_code": "LDN",
        **overrides,
    }


@pytest.fixture()
def cli(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """Point the job at the test database instead of the configured one."""
    monkeypatch.setattr(load_csv, "engine", engine)
    return CliRunner()


def players_in(engine: Engine) -> list[str]:
    with Session(engine) as session:
        return [player.full_name for player in session.exec(select(Player)).all()]


# --- reading -----------------------------------------------------------------


def test_read_csv_strips_values_and_numbers_lines(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path, "teams.csv", "﻿" + TEAMS_HEADER + " MUN , Man United , Man U \n"
    )

    assert load_csv.read_csv(source(path)) == [
        (2, {"code": "MUN", "full_name": "Man United", "short_name": "Man U"})
    ]


def test_read_csv_drops_columns_beyond_the_header(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path, "teams.csv", TEAMS_HEADER + "MUN,Man United,Man U,extra\n"
    )

    ((_, row),) = load_csv.read_csv(source(path))

    assert row == {"code": "MUN", "full_name": "Man United", "short_name": "Man U"}


# --- validation --------------------------------------------------------------


def test_parse_players_resolves_an_fa_code(session: Session) -> None:
    parsed, errors = load_csv.parse_players(session, [(2, player_row(country="USA"))])

    assert errors == []
    assert parsed[0].country_code == "US"


def test_parse_players_blanks_become_none(session: Session) -> None:
    parsed, _ = load_csv.parse_players(session, [(2, player_row(no="", team_code=""))])

    assert parsed[0].no is None
    assert parsed[0].team_code is None


def test_parse_players_reports_every_bad_row(session: Session) -> None:
    """One run should hand the operator the whole list, not the first problem."""
    rows = [
        (2, player_row(country="ZZ")),
        (3, player_row(full_name="   ")),
        (4, player_row(no="eleven")),
        (5, player_row(team_code="NOPE")),
        (6, player_row(country="")),
    ]

    parsed, errors = load_csv.parse_players(session, rows)

    assert parsed == []
    assert [error.line for error in errors] == [2, 3, 4, 5, 6]


def test_parse_players_rejects_an_out_of_range_number(session: Session) -> None:
    """The schema's 1-99 bound applies to the job for free."""
    _, errors = load_csv.parse_players(session, [(2, player_row(no="200"))])

    assert len(errors) == 1
    assert "no" in errors[0].message


# --- applying ----------------------------------------------------------------


def test_apply_players_creates_then_updates(session: Session) -> None:
    parsed, _ = load_csv.parse_players(session, [(2, player_row())])

    assert load_csv.apply_players(session, parsed) == (1, 0)
    assert load_csv.apply_players(session, parsed) == (0, 1)


def test_rows_sharing_a_name_in_one_file_update_each_other(session: Session) -> None:
    """The old loader built its id map once up front, so the second row 409'd."""
    parsed, _ = load_csv.parse_players(
        session,
        [(2, player_row(no="13")), (3, player_row(full_name="alex  morgan", no="9"))],
    )

    assert load_csv.apply_players(session, parsed) == (1, 1)

    found = session.exec(select(Player)).all()
    assert [(player.full_name, player.no) for player in found] == [("alex  morgan", 9)]


# --- the command ------------------------------------------------------------


def run(cli: CliRunner, command: str, path: Path) -> Result:
    return cli.invoke(load_csv.cli, [command, "--source", str(path)])


def test_loads_a_clean_file(cli: CliRunner, engine: Engine, tmp_path: Path) -> None:
    path = write_csv(tmp_path, "players.csv", PLAYERS_HEADER + MORGAN + KERR)

    result = run(cli, "players", path)

    assert result.exit_code == 0
    assert "created 2, updated 0" in result.output
    assert sorted(players_in(engine)) == ["Alex Morgan", "Sam Kerr"]


def test_reloading_the_same_file_updates(
    cli: CliRunner, engine: Engine, tmp_path: Path
) -> None:
    path = write_csv(tmp_path, "players.csv", PLAYERS_HEADER + MORGAN)
    run(cli, "players", path)

    result = run(cli, "players", path)

    assert result.exit_code == 0
    assert "created 0, updated 1" in result.output
    assert players_in(engine) == ["Alex Morgan"]


def test_a_single_bad_row_writes_nothing(
    cli: CliRunner, engine: Engine, tmp_path: Path
) -> None:
    """All or nothing: the good row on line 2 must not land either."""
    path = write_csv(
        tmp_path,
        "players.csv",
        PLAYERS_HEADER + MORGAN + "Sam Kerr,Kerr,forward,ZZ,20,\n",
    )

    result = run(cli, "players", path)

    assert result.exit_code == 1
    assert "players.csv:3" in result.output
    assert "nothing was written" in result.output
    assert players_in(engine) == []


def test_loads_teams(cli: CliRunner, engine: Engine, tmp_path: Path) -> None:
    path = write_csv(tmp_path, "teams.csv", TEAMS_HEADER + "MUN,Man United,Man U\n")

    result = run(cli, "teams", path)

    assert result.exit_code == 0
    with Session(engine) as session:
        codes = sorted(team.code for team in session.exec(select(Team)).all())
    assert codes == ["LDN", "MUN"]


def test_a_missing_file_is_a_usage_error(cli: CliRunner, tmp_path: Path) -> None:
    result = cli.invoke(
        load_csv.cli, ["players", "--source", str(tmp_path / "absent.csv")]
    )

    assert result.exit_code == 2


def test_the_default_source_comes_from_the_environment(
    cli: CliRunner, engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --source: the command composes <DATA_SOURCE>/<name>.csv itself."""
    write_csv(tmp_path, "players.csv", PLAYERS_HEADER + MORGAN)
    monkeypatch.setenv("DATA_SOURCE", str(tmp_path))

    result = cli.invoke(load_csv.cli, ["players"])

    assert result.exit_code == 0
    assert players_in(engine) == ["Alex Morgan"]


# --- deployment contract -----------------------------------------------------


def test_the_job_does_not_import_the_api(tmp_path: Path) -> None:
    """Cloud Run gives this job DATABASE_URL and nothing else.

    Importing app.main or anything under app.api would pull in AppSettings,
    which also demands CORS_ORIGINS, and the job would refuse to start over
    configuration for a request path it never serves.
    """
    probe = (
        "import sys, app.jobs.load_csv\n"
        "leaked = [n for n in sys.modules if n == 'app.main' or n.startswith('app.api')]\n"
        "sys.exit('job imports ' + ', '.join(leaked) if leaked else 0)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        # Away from backend/.env, so only the variables below are visible.
        cwd=tmp_path,
        env={
            "PATH": os.environ["PATH"],
            "PYTHONPATH": str(Path(app.__file__).parents[1]),
            "DATABASE_URL": "sqlite://",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
