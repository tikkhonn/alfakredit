from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

_ALTERS = [
    "ALTER TABLE application ADD COLUMN profile_changed BOOLEAN DEFAULT 0",
    "ALTER TABLE application ADD COLUMN extra_turnover INTEGER DEFAULT 0",
    "ALTER TABLE application ADD COLUMN collateral_msp BOOLEAN DEFAULT 0",
    "ALTER TABLE application ADD COLUMN pipeline JSON",
    "ALTER TABLE application ADD COLUMN profile_note TEXT",
]


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    for statement in _ALTERS:
        try:
            with engine.begin() as conn:
                conn.execute(text(statement))
        except Exception:
            continue


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
