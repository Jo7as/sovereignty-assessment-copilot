from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from conftest import ensure_database
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import settings
from app.models import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_migrations_match_models_and_can_be_reverted():
    main_database = make_url(settings.database_url).database
    url = ensure_database(f"{main_database}_migration_test")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []
    assert "service_variant" in inspect(engine).get_table_names()

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]

    engine.dispose()
