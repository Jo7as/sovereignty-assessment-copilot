from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings

engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3})


def database_is_reachable() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


def get_session() -> Iterator[Session]:
    """Eine Datenbanksitzung je Anfrage."""
    with Session(engine) as session:
        yield session


def get_session_factory() -> Callable[[], AbstractContextManager[Session]]:
    """Für Arbeit nach der Antwort, etwa einen Hintergrundlauf: Sie braucht eigene Sitzungen,
    weil die Sitzung der Anfrage dann schon geschlossen ist."""
    return lambda: Session(engine)
