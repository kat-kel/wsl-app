from sqlmodel import Session, select

from app.models import Team
from app.schemas.team import TeamCreate
from app.services.upsert import upsert


def find_team_by_code(session: Session, code: str) -> Team | None:
    """Look a team up by its natural key. Team's primary key is id, not code."""
    return session.exec(select(Team).where(Team.code == code)).first()


def team_exists(session: Session, code: str) -> bool:
    """Whether the natural key is taken, without loading the row.

    upsert_team writes through Core, which the ORM's identity map never sees, so
    loading the entity here would leave a stale copy behind for whoever reads it
    next.
    """
    return session.exec(select(Team.id).where(Team.code == code)).first() is not None


def upsert_team(session: Session, team_data: TeamCreate) -> bool:
    """Create the team, or overwrite whichever team already holds that code.

    Returns whether the row was new, which is the caller's report and nothing
    more: the write itself is atomic, so a run racing another can leave the
    count off by one without either run corrupting a row or failing.

    The caller owns the transaction and commits.
    """
    inserted = not team_exists(session, team_data.code)

    upsert(session, Team, team_data.model_dump(), key="code")

    return inserted
