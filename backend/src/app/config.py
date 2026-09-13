# Environment-backed settings
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_WRITE_API_KEY_LENGTH = 32


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class AppSettings(BaseSettings):
    database_url: str
    cors_origins: str
    # Comma-separated so several keys can be valid at once: during a rotation the
    # old and the new key are both accepted until every client has moved over.
    write_api_keys: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

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
def get_settings() -> AppSettings:
    return AppSettings()
