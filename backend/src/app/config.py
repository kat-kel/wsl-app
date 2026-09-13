# Environment-backed settings
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_WRITE_API_KEY_LENGTH = 32


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class DatabaseSettings(BaseSettings):
    """What a process needs to reach the database, and nothing else.

    Migrations are their own deploy step and never serve a request, so they read
    this rather than AppSettings. Keeping the two apart means the migration step
    is not handed an API key it has no use for, and cannot fail to start over a
    field that has nothing to do with the schema.
    """

    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


class AppSettings(DatabaseSettings):
    """Everything the API service needs, the database connection included.

    Every field here is required: the write routes are always mounted, so a
    deployment missing a key would serve them broken rather than not at all.
    """

    cors_origins: str
    # Comma-separated so several keys can be valid at once: during a rotation the
    # old and the new key are both accepted until every client has moved over.
    write_api_keys: str

    @field_validator("write_api_keys")
    @classmethod
    def validate_write_api_keys(cls, value: str) -> str:
        keys = _split_csv(value)
        if not keys:
            raise ValueError("at least one write API key is required")
        if any(len(key) < MIN_WRITE_API_KEY_LENGTH for key in keys):
            raise ValueError(
                f"every write API key must be at least "
                f"{MIN_WRITE_API_KEY_LENGTH} characters"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_csv(self.cors_origins)

    @property
    def write_api_key_list(self) -> list[str]:
        return _split_csv(self.write_api_keys)


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
