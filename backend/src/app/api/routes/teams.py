from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.security import require_write_access
from app.database import get_session
from app.models import Team
from app.schemas.team import TeamCreate, TeamRead

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post(
    "",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
def create_team(
    team_data: TeamCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Team:
    team = Team.model_validate(team_data)
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@router.get("", response_model=list[TeamRead])
def get_teams(session: Annotated[Session, Depends(get_session)]) -> list[Team]:
    statement = select(Team)
    teams = session.exec(statement).all()
    return teams


@router.put(
    "/{team_id}",
    response_model=TeamRead,
    dependencies=[Depends(require_write_access)],
)
def update_team(
    team_id: int,
    team_data: TeamCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found",
        )

    for field, value in team_data.model_dump().items():
        setattr(team, field, value)

    session.add(team)
    session.commit()
    session.refresh(team)
    return team
