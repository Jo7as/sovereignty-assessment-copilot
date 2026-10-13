from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3})


def database_is_reachable() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
