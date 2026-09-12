from io import TextIOWrapper
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session, select

from app.database import get_session
from app.models import Player
from app.schemas.player import PlayerCreate, PlayerImportResult, PlayerRead
from app.services.players import import_players_from_csv

router = APIRouter(prefix="/players", tags=["players"])


@router.post("", response_model=PlayerRead)
def create_player(
    player_data: PlayerCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Player:
    player = Player.model_validate(player_data)
    session.add(player)
    session.commit()
    session.refresh(player)
    return player


@router.get("", response_model=list[PlayerRead])
def get_players(
    session: Annotated[Session, Depends(get_session)],
) -> list[Player]:
    statement = select(Player)
    players = session.exec(statement).all()
    return players


@router.post("/import", response_model=PlayerImportResult)
def import_players(
    file: Annotated[UploadFile, File(description="CSV file containing player data")],
    session: Annotated[Session, Depends(get_session)],
) -> PlayerImportResult:
    text_file = TextIOWrapper(file.file, encoding="utf-8-sig", newline="")
    try:
        return import_players_from_csv(text_file, session)
    finally:
        text_file.detach()
