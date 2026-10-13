import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Base


def ensure_database(name: str) -> URL:
    """Legt die Datenbank `name` an, falls sie fehlt, und gibt ihre Adresse zurück."""
    main_url = make_url(settings.database_url)
    admin_engine = create_engine(main_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine.dispose()
    return main_url.set(database=name)


@pytest.fixture(scope="session")
def test_engine():
    """Eigene Testdatenbank, damit Tests die echten Daten nie anfassen."""
    main_database = make_url(settings.database_url).database
    engine = create_engine(ensure_database(f"{main_database}_test"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine):
    """Jeder Test läuft in einer Transaktion, die am Ende verworfen wird."""
    with test_engine.connect() as connection:
        transaction = connection.begin()
        with Session(connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
