from enum import StrEnum

from sqlalchemy import case, func, nullslast
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models import Country, Player, Team
from app.schemas.player import PlayerCreate
from app.services.errors import UnknownReference
from app.services.upsert import upsert


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


def resolve_country_code(session: Session, value: str) -> str | None:
    """Turn either an ISO code (US) or an FA code (USA) into the stored ISO code.

    Data sources disagree about which of the two they publish, so both are
    accepted on the way in and only the ISO code is ever persisted.
    """
    code = value.strip().upper()
    if session.get(Country, code) is not None:
        return code

    country = session.exec(select(Country).where(Country.fa_code == code)).first()
    return country.code if country is not None else None


def validate_references(player_data: PlayerCreate, session: Session) -> None:
    """Reject unknown country/team codes before the database raises on the FK."""
    if session.get(Country, player_data.country_code) is None:
        raise UnknownReference(f"Unknown country_code {player_data.country_code!r}")

    if player_data.team_code is None:
        return

    team = session.exec(select(Team).where(Team.code == player_data.team_code)).first()
    if team is None:
        raise UnknownReference(f"Unknown team_code {player_data.team_code!r}")


def player_exists(session: Session, full_name: str) -> bool:
    """Whether the natural key is taken, without loading the row.

    upsert_player writes through Core, which the ORM's identity map never sees,
    so loading the entity here would leave a stale copy behind for whoever reads
    it next.
    """
    return (
        session.exec(
            select(Player.id).where(Player.normalized_name == normalize_name(full_name))
        ).first()
        is not None
    )


def upsert_player(session: Session, player_data: PlayerCreate) -> bool:
    """Create the player, or overwrite whoever already holds that normalized name.

    Returns whether the row was new, which is the caller's report and nothing
    more: the write itself is atomic, so a run racing another can leave the
    count off by one without either run corrupting a row or failing.

    The caller owns the transaction and commits.
    """
    validate_references(player_data, session)

    inserted = not player_exists(session, player_data.full_name)

    upsert(
        session,
        Player,
        player_data.model_dump()
        | {"normalized_name": normalize_name(player_data.full_name)},
        key="normalized_name",
    )

    return inserted
