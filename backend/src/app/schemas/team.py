from pydantic import BaseModel, Field, field_validator

from app.models.team import (
    TEAM_CODE_MAX_LENGTH,
    TEAM_FULL_NAME_MAX_LENGTH,
    TEAM_SHORT_NAME_MAX_LENGTH,
)


class TeamCreate(BaseModel):
    code: str = Field(min_length=1, max_length=TEAM_CODE_MAX_LENGTH)
    full_name: str = Field(min_length=1, max_length=TEAM_FULL_NAME_MAX_LENGTH)
    short_name: str = Field(min_length=1, max_length=TEAM_SHORT_NAME_MAX_LENGTH)

    @field_validator("code", "full_name", "short_name", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class TeamRead(TeamCreate):
    id: int
