from pydantic import BaseModel, Field, field_validator

from app.models.country import COUNTRY_CODE_MAX_LENGTH
from app.models.player import (
    PLAYER_NAME_MAX_LENGTH,
    POSITION_MAX_LENGTH,
    SHIRT_NAME_MAX_LENGTH,
)
from app.models.team import TEAM_CODE_MAX_LENGTH


class PlayerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=PLAYER_NAME_MAX_LENGTH)
    shirt_name: str = Field(min_length=1, max_length=SHIRT_NAME_MAX_LENGTH)
    position: str = Field(min_length=1, max_length=POSITION_MAX_LENGTH)
    country_code: str = Field(min_length=1, max_length=COUNTRY_CODE_MAX_LENGTH)
    no: int | None = Field(default=None, ge=1, le=99)
    team_code: str | None = Field(default=None, max_length=TEAM_CODE_MAX_LENGTH)

    @field_validator(
        "full_name",
        "shirt_name",
        "position",
        "country_code",
        "team_code",
        mode="before",
    )
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class PlayerRead(PlayerCreate):
    id: int
    normalized_name: str
