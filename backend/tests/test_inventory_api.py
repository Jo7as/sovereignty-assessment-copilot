from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.inventory.api import get_classifier
from app.main import app
from app.seed import load_seed

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(autouse=True)
def seeded_database(session):
    """Die Tests nutzen die Testdatenbank mit den echten Anbieterdaten und keine KI."""
    load_seed(session, DATA_DIR)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_classifier] = lambda: None
    yield
    app.dependency_overrides.clear()


TESTDATA = Path(__file__).resolve().parents[2] / "data" / "testdata"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def upload(name: str, content: bytes, content_type: str = XLSX):
    return client.post("/inventory/import", files={"file": (name, content, content_type)})


def test_musterbank_upload_returns_all_entries():
    response = upload("musterbank.xlsx", (TESTDATA / "musterbank-it-bestand.xlsx").read_bytes())

    body = response.json()
    assert response.status_code == 200
    assert body["valid"] is True
    assert len(body["entries"]) == 58
    assert body["entries"][0]["service"] == "Avaloq Banking Suite"
    assert body["entries"][0]["criticality"] == "HOCH"


def test_every_entry_carries_its_match_and_review_flag():
    response = upload("musterbank.xlsx", (TESTDATA / "musterbank-it-bestand.xlsx").read_bytes())

    body = response.json()
    avaloq = body["entries"][0]["match"]
    outlook = next(e for e in body["entries"] if e["service"] == "Outlook")["match"]
    assert (avaloq["service"], avaloq["method"], avaloq["needs_review"]) == (
        "avaloq",
        "TEXT",
        False,
    )
    assert (outlook["service"], outlook["needs_review"]) == (None, True)
    assert body["needs_review"] == sum(e["match"]["needs_review"] for e in body["entries"])


def test_upload_with_errors_lists_them_and_is_not_valid():
    csv = "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion\nSlack;Chat;sehr hoch;nein\n"

    body = upload("bestand.csv", csv.encode(), "text/csv").json()

    assert body["valid"] is False
    assert body["errors"][0]["row"] == 2
    assert body["errors"][0]["column"] == "Kritikalität *"


def test_unsupported_file_type_is_rejected_with_415():
    response = upload("bestand.pdf", b"%PDF", "application/pdf")

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_broken_file_is_rejected_with_400():
    response = upload("bestand.xlsx", b"kein zip")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNREADABLE_FILE"


def test_too_large_file_is_rejected_with_413():
    response = upload("bestand.csv", b"x" * (5 * 1024 * 1024 + 1), "text/csv")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_template_can_be_downloaded():
    response = client.get("/inventory/template")

    assert response.status_code == 200
    assert response.headers["content-type"] == XLSX
    assert "it-bestand-vorlage.xlsx" in response.headers["content-disposition"]
    assert response.content[:2] == b"PK"  # Excel-Dateien sind ZIP-Archive
