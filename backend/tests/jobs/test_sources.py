from pathlib import Path

import click
import pytest

from app.jobs.sources import DEFAULT_BASE, Source, base, resolve

BUCKET = "gs://wsl-data/latest"


def test_base_defaults_to_the_repo_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATA_SOURCE", raising=False)

    assert base() == DEFAULT_BASE


def test_base_drops_a_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    """So composing a URI never produces a doubled separator."""
    monkeypatch.setenv("DATA_SOURCE", BUCKET + "/")

    assert base() == BUCKET


def test_resolve_composes_the_file_name_onto_the_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_SOURCE", BUCKET)

    assert resolve("players", None).uri == f"{BUCKET}/players.csv"


def test_an_explicit_source_wins_over_the_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_SOURCE", BUCKET)
    path = tmp_path / "other.csv"
    path.write_text("code\n", encoding="utf-8")

    assert resolve("players", str(path)).uri == str(path)


def test_a_remote_uri_is_not_checked_against_the_disk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bucket object can only be checked by fetching it, so resolve must not try."""
    monkeypatch.setenv("DATA_SOURCE", BUCKET)

    assert resolve("teams", None).is_remote


def test_a_missing_local_file_is_a_usage_error(tmp_path: Path) -> None:
    with pytest.raises(click.BadParameter):
        resolve("players", str(tmp_path / "absent.csv"))


def test_name_is_the_last_segment_of_either_kind_of_uri() -> None:
    """Error lines read `players.csv:14` whether the file is local or remote."""
    assert Source(f"{BUCKET}/players.csv").name == "players.csv"
    assert Source("/app/fixtures/players.csv").name == "players.csv"


def test_opening_a_remote_source_is_not_implemented_yet() -> None:
    """Placeholder for the GCS client; the bucket does not exist yet."""
    with (
        pytest.raises(NotImplementedError, match="not implemented yet"),
        Source(f"{BUCKET}/players.csv").open(),
    ):
        pass  # pragma: no cover
