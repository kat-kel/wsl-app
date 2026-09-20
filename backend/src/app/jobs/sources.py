"""Where the load job reads a CSV from.

Local development reads a file from disk. Staging and production read the object
a separate scraper project writes to a GCS bucket; that project never touches
this database, and this one never scrapes -- a bucket is the only thing they
share. Because only the URI differs, the source is configuration rather than a
second code path: parsing, validation and loading downstream are identical.

DATA_SOURCE holds the base location and each command appends its own file name,
so one variable covers every entity:

    DATA_SOURCE=/app/fixtures         ->  /app/fixtures/players.csv
    DATA_SOURCE=gs://wsl-data/latest  ->  gs://wsl-data/latest/players.csv
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import click

GCS_SCHEME = "gs://"

# Relative, so running the job from the repo root outside Docker finds the
# committed fixtures. Compose sets DATA_SOURCE to the mount path instead.
DEFAULT_BASE = "fixtures"

_GCS_NOT_IMPLEMENTED = """\
reading from {scheme} is not implemented yet ({uri}).

Planned: add google-cloud-storage, then open the blob as text here and let the
rest of the job work unchanged. The Cloud Run job's service account needs
roles/storage.objectViewer on the bucket and nothing more.

Until then, point DATA_SOURCE at a local directory."""


@dataclass(frozen=True)
class Source:
    """One CSV to read: its URI, and the short name errors are reported against."""

    uri: str

    @property
    def is_remote(self) -> bool:
        return self.uri.startswith(GCS_SCHEME)

    @property
    def name(self) -> str:
        """The last segment, so a message reads `players.csv:14` either way."""
        return self.uri.rsplit("/", 1)[-1]

    @contextmanager
    def open(self) -> Iterator[TextIO]:
        """A text stream of the CSV, whatever it is stored on.

        utf-8-sig strips the BOM a spreadsheet export leaves behind.
        """
        if self.is_remote:
            raise NotImplementedError(
                _GCS_NOT_IMPLEMENTED.format(scheme=GCS_SCHEME, uri=self.uri)
            )

        with Path(self.uri).open(encoding="utf-8-sig", newline="") as file:
            yield file


def base() -> str:
    return os.environ.get("DATA_SOURCE", DEFAULT_BASE).rstrip("/")


def resolve(name: str, uri: str | None) -> Source:
    """An explicit --source if given, otherwise <DATA_SOURCE>/<name>.csv.

    A local path is checked here so that a typo fails as a usage error before
    the job opens a database session. A remote URI can only be checked by
    fetching it, which is the source's own job.
    """
    source = Source(uri if uri is not None else f"{base()}/{name}.csv")

    if not source.is_remote and not Path(source.uri).is_file():
        raise click.BadParameter(f"no such file: {source.uri}", param_hint="'--source'")

    return source
