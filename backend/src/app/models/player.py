from sqlmodel import Field, SQLModel

from app.models.country import COUNTRY_CODE_MAX_LENGTH
from app.models.team import TEAM_CODE_MAX_LENGTH

PLAYER_NAME_MAX_LENGTH = 120
SHIRT_NAME_MAX_LENGTH = 60
POSITION_MAX_LENGTH = 30


class Player(SQLModel, table=True):
    __tablename__ = "players"

    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=PLAYER_NAME_MAX_LENGTH)
    normalized_name: str = Field(
        unique=True, index=True, max_length=PLAYER_NAME_MAX_LENGTH
    )
    shirt_name: str = Field(max_length=SHIRT_NAME_MAX_LENGTH)
    country_code: str = Field(
        index=True, foreign_key="countries.code", max_length=COUNTRY_CODE_MAX_LENGTH
    )
    position: str = Field(index=True, max_length=POSITION_MAX_LENGTH)
    no: int | None = Field(default=None)
    team_code: str | None = Field(
        default=None,
        index=True,
        foreign_key="teams.code",
        max_length=TEAM_CODE_MAX_LENGTH,
    )
