"""Braucht die laufende Datenbank: `docker compose up -d` im Projektstamm."""

from sqlalchemy import text

from app.db import database_is_reachable, engine


def test_database_is_reachable():
    assert database_is_reachable() is True


def test_database_is_postgresql_17():
    with engine.connect() as connection:
        version = connection.execute(text("SHOW server_version")).scalar_one()

    assert version.startswith("17.")
