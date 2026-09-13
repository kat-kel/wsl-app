from sqlmodel import Field, SQLModel

COUNTRY_CODE_MAX_LENGTH = 8
FA_CODE_MAX_LENGTH = 3
COUNTRY_NAME_MAX_LENGTH = 100


class Country(SQLModel, table=True):
    __tablename__ = "countries"

    code: str = Field(primary_key=True, max_length=COUNTRY_CODE_MAX_LENGTH)
    fa_code: str = Field(unique=True, index=True, max_length=FA_CODE_MAX_LENGTH)
    name: str = Field(max_length=COUNTRY_NAME_MAX_LENGTH)
