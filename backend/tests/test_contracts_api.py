"""Verträge am Assessment: hochladen, Text seitenweise lesen, auflisten, löschen.

Arbeitsanweisung docs/tiefenpruefung-ablauf.md, Schritt 1 (Aufnehmen).
"""

import pytest
from fastapi.testclient import TestClient

from app.contracts import UnreadablePdf, read_pages
from app.db import get_session
from app.main import app
from app.models import AssessmentContract

client = TestClient(app)


def make_pdf(*pages: str) -> bytes:
    """Ein kleines, gültiges PDF mit einer Textzeile je Seite. Leerer Text = Seite ohne Text."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", ""]
    kids = []
    for text in pages:
        content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET" if text else ""
        page_number, content_number = len(objects) + 1, len(objects) + 2
        kids.append(f"{page_number} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_number} 0 R"
            " /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
            " >> >> >>"
        )
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>"
    body, offsets = b"%PDF-1.4\n", []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += f"{number} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    body += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    body += trailer.encode()
    return body


AVV = make_pdf(
    "Vertrag ueber die Auftragsverarbeitung",
    "",
    "Die Verarbeitung erfolgt ausschliesslich in der EU.",
)


@pytest.fixture(autouse=True)
def database(session):
    app.dependency_overrides[get_session] = lambda: session
    yield
    app.dependency_overrides.clear()


def create() -> int:
    return client.post("/assessments", json={"name": "Musterbank AG"}).json()["id"]


def upload(assessment_id: int, content: bytes = AVV, name: str = "avv.pdf"):
    return client.post(
        f"/assessments/{assessment_id}/contracts",
        files={"file": (name, content, "application/pdf")},
    )


# ---------------------------------------------------------------- Text lesen


def test_pages_are_read_in_order_and_pages_without_text_stay_empty():
    pages = read_pages(AVV)

    assert len(pages) == 3
    assert "Auftragsverarbeitung" in pages[0]
    assert pages[1] == ""
    assert "ausschliesslich in der EU" in pages[2]


def test_null_characters_are_removed_because_the_database_rejects_them(monkeypatch):
    import app.contracts as contracts

    class Page:
        def extract_text(self):
            return "Die Kunden\x00daten bleiben in der EU"

    class Reader:
        pages = [Page()]

        def __init__(self, stream):
            pass

    monkeypatch.setattr(contracts, "PdfReader", Reader)

    assert read_pages(b"%PDF-") == ["Die Kundendaten bleiben in der EU"]


def test_broken_pdf_is_unreadable():
    with pytest.raises(UnreadablePdf):
        read_pages(b"%PDF-1.4 kaputt")


# ---------------------------------------------------------------- Hochladen


def test_uploaded_contract_is_stored_with_its_pages(session):
    assessment_id = create()

    response = upload(assessment_id)

    body = response.json()
    stored = session.get(AssessmentContract, body["id"])
    assert response.status_code == 201
    assert body["filename"] == "avv.pdf"
    assert body["page_count"] == 3
    assert body["pages_without_text"] == [2]
    assert body["service"] is None and body["document_type"] is None
    assert stored.content == AVV
    assert "ausschliesslich in der EU" in stored.pages[2]


def test_several_contracts_can_be_uploaded_and_listed():
    assessment_id = create()
    upload(assessment_id, name="avv.pdf")
    upload(assessment_id, make_pdf("Rahmenvertrag ueber Cloud-Dienste"), name="rahmenvertrag.pdf")

    contracts = client.get(f"/assessments/{assessment_id}/contracts").json()["contracts"]

    assert [contract["filename"] for contract in contracts] == ["avv.pdf", "rahmenvertrag.pdf"]
    assert "pages" not in contracts[0]  # der Text bleibt in der Liste weg


def test_pdf_without_any_text_is_rejected_and_not_stored(session):
    assessment_id = create()

    response = upload(assessment_id, make_pdf("", ""), name="scan.pdf")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_TEXT"
    assert session.query(AssessmentContract).count() == 0


def test_only_pdf_files_are_accepted():
    assessment_id = create()

    by_name = upload(assessment_id, AVV, name="avv.docx")
    by_content = upload(assessment_id, b"PK\x03\x04 Word-Datei", name="avv.pdf")

    assert by_name.status_code == 415
    assert by_content.status_code == 400
    assert by_content.json()["error"]["code"] == "UNREADABLE_FILE"


def test_too_large_file_is_rejected(monkeypatch):
    import app.contracts.api as api

    monkeypatch.setattr(api, "MAX_FILE_SIZE", 100)

    response = upload(create())

    assert response.status_code == 413


def test_contract_for_unknown_assessment_gives_404():
    assert upload(999_999).status_code == 404


# ---------------------------------------------------------------- Löschen


def test_contract_can_be_deleted(session):
    assessment_id = create()
    contract_id = upload(assessment_id).json()["id"]

    response = client.delete(f"/assessments/{assessment_id}/contracts/{contract_id}")

    assert response.status_code == 204
    assert session.get(AssessmentContract, contract_id) is None


def test_contract_of_another_assessment_cannot_be_deleted():
    contract_id = upload(create()).json()["id"]

    response = client.delete(f"/assessments/{create()}/contracts/{contract_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONTRACT_NOT_FOUND"
