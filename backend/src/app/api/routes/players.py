from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.security import require_write_access
from app.database import get_session
from app.models import Player
from app.schemas.player import PlayerCreate, PlayerRead
from app.services.players import (
    PlayerSort,
    normalize_name,
    select_players,
    validate_references,
)

router = APIRouter(prefix="/players", tags=["players"])


@router.post(
    "",
    response_model=PlayerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
def create_player(
    player_data: PlayerCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Player:
    validate_references(player_data, session)

    normalized_name = normalize_name(player_data.full_name)
    existing = session.exec(
        select(Player).where(Player.normalized_name == normalized_name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Player {player_data.full_name!r} already exists",
        )

    player = Player(**player_data.model_dump(), normalized_name=normalized_name)
    session.add(player)
    session.commit()
    session.refresh(player)
    return player


@router.get("", response_model=list[PlayerRead])
def get_players(
    session: Annotated[Session, Depends(get_session)],
    sort: Annotated[
        PlayerSort,
        Query(description="Order of the returned players."),
    ] = PlayerSort.NAME,
) -> list[Player]:
    return session.exec(select_players(sort)).all()


@router.put(
    "/{player_id}",
    response_model=PlayerRead,
    dependencies=[Depends(require_write_access)],
)
def update_player(
    player_id: int,
    player_data: PlayerCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Player:
    player = session.get(Player, player_id)
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found",
        )

    validate_references(player_data, session)

    for field, value in player_data.model_dump().items():
        setattr(player, field, value)
    player.normalized_name = normalize_name(player_data.full_name)

    session.add(player)
    session.commit()
    session.refresh(player)
    return player
