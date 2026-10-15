from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
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
