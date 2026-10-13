from fastapi.testclient import TestClient

from app.db import database_is_reachable
from app.main import app

client = TestClient(app)


def test_health_returns_ok_when_database_is_reachable():
    app.dependency_overrides[database_is_reachable] = lambda: True
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable():
    app.dependency_overrides[database_is_reachable] = lambda: False
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unreachable"}
