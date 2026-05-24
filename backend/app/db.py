from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def init_db(data_dir: str) -> None:
    global engine, SessionLocal

    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "uploads").mkdir(parents=True, exist_ok=True)

    db_path = path / "db.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from app.models import document  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
