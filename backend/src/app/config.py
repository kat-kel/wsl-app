# Environment-backed settings
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class DatabaseSettings(BaseSettings):
    """What a process needs to reach the database with a write-capable role.

    Migrations and the CSV load job are the only two things that ever change a
    row, so they are also the only two things trusted with DATABASE_URL. Both
    are their own deploy steps that never serve a request, so they read this
    rather than AppSettings.
    """

    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


class AppSettings(DatabaseSettings):
    """Everything the API service needs.

    `database_url` is overridden rather than inherited: it comes from
    API_DATABASE_URL, a credential bound to a Postgres role that can only
    SELECT (see deploy/db-init/). A write route added to the API by mistake
    would still fail at the database, not only in code review.
    """

    database_url: str = Field(validation_alias="API_DATABASE_URL")
    cors_origins: str

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_csv(self.cors_origins)


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
