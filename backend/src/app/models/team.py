from sqlmodel import Field, SQLModel

TEAM_CODE_MAX_LENGTH = 8
TEAM_FULL_NAME_MAX_LENGTH = 100
TEAM_SHORT_NAME_MAX_LENGTH = 60


class Team(SQLModel, table=True):
    __tablename__ = "teams"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=TEAM_CODE_MAX_LENGTH)
    full_name: str = Field(max_length=TEAM_FULL_NAME_MAX_LENGTH)
    short_name: str = Field(max_length=TEAM_SHORT_NAME_MAX_LENGTH)
