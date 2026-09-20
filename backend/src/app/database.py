# Engine, session dependency, transaction helpers -- for the API only.
#
# Built from AppSettings, so this always connects with the read-only role. The
# load job and Alembic each build their own write-capable engine instead of
# importing this one.
from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
