from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Team
from app.schemas.team import TeamRead

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
def get_teams(session: Annotated[Session, Depends(get_session)]) -> list[Team]:
    statement = select(Team)
    teams = session.exec(statement).all()
    return teams
