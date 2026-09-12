from pydantic import BaseModel, Field, field_validator


class PlayerImportRead(BaseModel):
    name: str
    position: str
    country: str

    @field_validator("name", "position", "country", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @property
    def normalized_name(self) -> str:
        return " ".join(self.name.strip().casefold().split())


class PlayerCreate(BaseModel):
    display_name: str
    normalized_name: str = Field(json_schema_extra={"unique": True, "index": True})
    position: str | None = None
    country: str | None = None


class PlayerRead(PlayerCreate):
    id: int


class PlayerImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]
    total_rows: int
    already_existing: int
    duplicates_in_file: int
