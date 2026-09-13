from enum import StrEnum

from sqlalchemy import case, func, nullslast
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models import Country, Player, Team
from app.schemas.player import PlayerCreate


class UnknownReference(Exception):
    """A player refers to a country or team that does not exist."""


def normalize_name(full_name: str) -> str:
    return " ".join(full_name.casefold().split())


class PlayerSort(StrEnum):
    NAME = "name"
    NUMBER = "number"
    POSITION = "position"
    POSITION_NAME = "position_name"


# Ranked rather than sorted alphabetically so the order reads like a team sheet.
# An unrecognised position sorts last instead of failing the query.
POSITION_RANK = case(
    {"goalkeeper": 0, "defender": 1, "midfielder": 2, "forward": 3},
    value=func.lower(Player.position),
    else_=99,
)

BY_NAME = func.lower(Player.shirt_name)
BY_NUMBER = nullslast(Player.no.asc())

SORT_ORDERS = {
    PlayerSort.NAME: (BY_NAME,),
    PlayerSort.NUMBER: (BY_NUMBER,),
    PlayerSort.POSITION: (POSITION_RANK, BY_NUMBER),
    PlayerSort.POSITION_NAME: (POSITION_RANK, BY_NAME),
}


def select_players(sort: PlayerSort) -> SelectOfScalar[Player]:
    # id breaks remaining ties so equal keys never swap places between requests.
    return select(Player).order_by(*SORT_ORDERS[sort], Player.id)


def validate_references(player_data: PlayerCreate, session: Session) -> None:
    """Reject unknown country/team codes before the database raises on the FK."""
    if session.get(Country, player_data.country_code) is None:
        raise UnknownReference(f"Unknown country_code {player_data.country_code!r}")

    if player_data.team_code is None:
        return

    team = session.exec(select(Team).where(Team.code == player_data.team_code)).first()
    if team is None:
        raise UnknownReference(f"Unknown team_code {player_data.team_code!r}")
