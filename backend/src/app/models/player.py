from sqlmodel import Field, SQLModel


class Player(SQLModel, table=True):
    __tablename__ = "players"

    id: int | None = Field(default=None, primary_key=True)
    display_name: str
    normalized_name: str
    country: str = Field(index=True)
    position: str = Field(index=True)
