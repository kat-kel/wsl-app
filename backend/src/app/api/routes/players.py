from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.models import Player
from app.schemas.player import PlayerRead
from app.services import players as player_service

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=list[PlayerRead])
def get_players(
    session: Annotated[Session, Depends(get_session)],
    sort: Annotated[
        player_service.PlayerSort,
        Query(description="Order of the returned players."),
    ] = player_service.PlayerSort.NAME,
) -> list[Player]:
    return session.exec(player_service.select_players(sort)).all()
