from pydantic import BaseModel


class CountryRead(BaseModel):
    code: str
    fa_code: str
    name: str
