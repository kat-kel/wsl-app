from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Country
from app.schemas.country import CountryRead

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=list[CountryRead])
def get_countries(
    session: Annotated[Session, Depends(get_session)],
) -> list[Country]:
    statement = select(Country).order_by(Country.name)
    return session.exec(statement).all()
