from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.inventory.api import get_classifier
from app.main import app
from app.seed import load_seed

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def seeded_database(session):
    load_seed(session, DATA_DIR)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_classifier] = lambda: None
    yield
    app.dependency_overrides.clear()


def test_musterbank_preview_returns_services_portfolio_and_open_entries():
    content = (DATA_DIR / "testdata" / "musterbank-it-bestand.xlsx").read_bytes()

    response = client.post("/assessments/preview", files={"file": ("m.xlsx", content, XLSX)})

    body = response.json()
    assert response.status_code == 200
    assert len(body["services"]) == 46
    assert len(body["unmatched"]) == 6
    first = body["services"][0]
    assert set(first["objectives"]) == {
        "STRATEGISCH", "RECHTLICH", "DATEN_KI", "OPERATIV",
        "LIEFERKETTE", "TECHNOLOGIE", "SICHERHEIT", "UMWELT",
    }  # fmt: skip
    finding = first["objectives"]["STRATEGISCH"]["findings"][0]
    assert {"criterion", "ceiling", "potential", "reason", "fact", "is_gap"} <= set(finding)
    assert 0 <= body["portfolio"]["score"] <= body["portfolio"]["potential_score"] <= 100
    waves = body["roadmap"]["waves"]
    assert [wave["wave"] for wave in waves] == [1, 2, 3]
    assert waves[0]["items"][0]["title"].startswith(("Kernfrage", "2 Kernfragen", "3 Kernfragen"))
    assert all(q["text"].endswith("?") for q in body["roadmap"]["questions"])


def test_inventory_with_errors_is_not_assessed():
    csv = "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion\nSlack;Chat;sehr hoch;nein\n"

    response = client.post(
        "/assessments/preview", files={"file": ("b.csv", csv.encode(), "text/csv")}
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_INVENTORY"
    assert error["details"] == [
        {
            "row": 2,
            "column": "Kritikalität *",
            "message": "„sehr hoch“ ist nicht erlaubt. Erlaubt: gering, mittel, hoch.",
        }
    ]


def test_demo_assesses_the_musterbank_without_upload():
    response = client.get("/assessments/demo")

    body = response.json()
    assert response.status_code == 200
    assert body["inventory"]["name"] == "Musterbank AG"
    assert len(body["services"]) == 46


def test_each_service_carries_its_evidence():
    body = client.get("/assessments/demo").json()

    m365 = next(s for s in body["services"] if s["service"] == "microsoft-365")
    attributes = {item["attribute"] for item in m365["evidence"]}
    assert {"data_location", "key_management", "ultimate_parent"} <= attributes
    item = next(i for i in m365["evidence"] if i["attribute"] == "data_location")
    assert item["source_url"].startswith("https://")
    assert item["quote"]


def test_browser_requests_from_the_frontend_are_allowed():
    response = client.options(
        "/assessments/demo",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_browser_requests_from_other_origins_are_not_allowed():
    response = client.options(
        "/assessments/demo",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers
