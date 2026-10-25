from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.inventory.api import get_classifier
from app.main import app
from app.matching import AiChoice
from app.models import AssessmentAnswer, InventoryMatch
from app.seed import load_seed

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MUSTERBANK = (DATA_DIR / "testdata" / "musterbank-it-bestand.xlsx").read_bytes()
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_HEADER = "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion;Exit-Plan vorhanden\n"


@pytest.fixture(autouse=True)
def database(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_classifier] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def seeded(session):
    load_seed(session, DATA_DIR)
    return session


def upload(assessment_id: int, content: bytes = MUSTERBANK, name: str = "musterbank.xlsx"):
    kind = XLSX if name.endswith(".xlsx") else "text/csv"
    return client.put(
        f"/assessments/{assessment_id}/inventory", files={"file": (name, content, kind)}
    )


def csv(*lines: str) -> bytes:
    return (CSV_HEADER + "\n".join(lines) + "\n").encode()


def create(name: str = "Musterbank AG") -> dict:
    response = client.post("/assessments", json={"name": name})
    assert response.status_code == 201
    return response.json()


def put_answers(assessment_id: int, answers: dict):
    return client.put(f"/assessments/{assessment_id}/answers", json={"answers": answers})


def test_questionnaire_lists_questions_with_legal_basis():
    body = client.get("/questionnaire").json()

    exit_strategy = next(q for q in body["questions"] if q["key"] == "exit_strategy")

    assert len(body["questions"]) == 27
    assert exit_strategy["basis"][0]["article"] == "Art. 28 Abs. 8"
    assert exit_strategy["basis"][0]["retrieved"] == "2026-10-19"


def test_new_assessment_starts_empty():
    body = create("  Musterbank AG  ")

    assert body["name"] == "Musterbank AG"
    assert body["questionnaire_version"] == 1
    assert body["answers"] == {}
    assert body["progress"] == {"answered": 0, "total": 27}
    assert (body["maturity"]["secured"], body["maturity"]["possible"]) == (0.0, 4.0)


@pytest.mark.parametrize("payload", [{"name": "   "}, {"name": "x" * 201}, {}])
def test_assessment_needs_a_name(payload):
    response = client.post("/assessments", json=payload)

    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"][0]["location"].startswith("body")


def test_answers_are_saved_and_returned():
    assessment = create()

    response = put_answers(
        assessment["id"], {"sector": "KREDITINSTITUT", "employees": 180, "exit_strategy": "ALLE"}
    )

    stored = client.get(f"/assessments/{assessment['id']}").json()
    assert response.status_code == 200
    assert stored["answers"] == {
        "sector": "KREDITINSTITUT",
        "employees": 180,
        "exit_strategy": "ALLE",
    }
    assert stored["progress"]["answered"] == 3
    exit_dimension = next(d for d in stored["maturity"]["dimensions"] if d["key"] == "EXIT")
    assert (exit_dimension["secured"], exit_dimension["answered"]) == (0.6, 1)


def test_decimal_numbers_keep_their_value():
    assessment = create()

    body = put_answers(assessment["id"], {"annual_turnover": 42.5}).json()

    assert body["answers"] == {"annual_turnover": 42.5}


def test_later_answers_change_only_what_they_name():
    assessment = create()
    put_answers(assessment["id"], {"sector": "KREDITINSTITUT", "exit_strategy": "NEIN"})

    body = put_answers(assessment["id"], {"exit_strategy": "ALLE_UEBERPRUEFT"}).json()

    assert body["answers"] == {"sector": "KREDITINSTITUT", "exit_strategy": "ALLE_UEBERPRUEFT"}


def test_changing_an_answer_does_not_create_a_second_row(session):
    assessment = create()
    put_answers(assessment["id"], {"employees": 180})

    put_answers(assessment["id"], {"employees": 200})

    rows = session.query(AssessmentAnswer).filter_by(assessment_id=assessment["id"]).all()
    assert [(row.question_key, row.number_value) for row in rows] == [("employees", 200)]


def test_null_deletes_an_answer():
    assessment = create()
    put_answers(assessment["id"], {"sector": "KREDITINSTITUT", "employees": 180})

    body = put_answers(assessment["id"], {"sector": None}).json()

    assert body["answers"] == {"employees": 180}


def test_one_invalid_answer_saves_nothing():
    assessment = create()

    response = put_answers(
        assessment["id"], {"sector": "KREDITINSTITUT", "employees": "viele", "farbe": "BLAU"}
    )

    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "INVALID_ANSWERS"
    assert error["message"].startswith("2 Antworten sind ungültig")
    assert [problem["question"] for problem in error["details"]] == ["employees", "farbe"]
    assert client.get(f"/assessments/{assessment['id']}").json()["answers"] == {}


def test_empty_answers_are_rejected():
    assessment = create()

    response = put_answers(assessment["id"], {})

    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_unknown_assessment_gives_404():
    assert client.get("/assessments/999999").json()["error"]["code"] == "ASSESSMENT_NOT_FOUND"
    assert put_answers(999999, {"sector": "ANDERER"}).status_code == 404


def test_demo_route_is_not_mistaken_for_an_assessment_id():
    response = client.get("/assessments/demo")

    assert response.status_code == 200
    assert response.json()["inventory"]["name"] == "Musterbank AG"


def test_assessment_shows_regulation_and_open_obligations():
    assessment = create()

    body = put_answers(
        assessment["id"],
        {"sector": "KREDITINSTITUT", "employees": 400, "exit_strategy": "NEIN"},
    ).json()

    regulation = body["regulation"]
    assert regulation["dora"]["status"] == "GILT"
    assert (regulation["nis2"]["status"], regulation["nis2"]["entity_class"]) == (
        "GILT",
        "WESENTLICH",
    )
    assert regulation["dora_precedes_nis2"] is True
    assert regulation["applicable_laws"] == ["DORA"]
    assert [hint["question"] for hint in regulation["hints"]] == ["exit_strategy"]
    assert regulation["hints"][0]["basis"][0]["retrieved"] == "2026-10-19"
    assert "exit_tested" in regulation["unanswered_obligations"]


def test_new_assessment_cannot_determine_the_regulation_yet():
    regulation = create()["regulation"]

    assert (regulation["dora"]["status"], regulation["nis2"]["status"]) == (
        "NICHT_BESTIMMBAR",
        "NICHT_BESTIMMBAR",
    )
    assert regulation["hints"] == []


# ---------------------------------------------------------------- IT-Bestand am Assessment


def test_new_assessment_has_no_inventory():
    assert create()["inventory"] is None


def test_uploaded_inventory_is_assessed_with_the_assessment(seeded):
    assessment = create()

    body = upload(assessment["id"]).json()

    inventory = body["inventory"]
    assert inventory["inventory"]["name"] == "musterbank.xlsx"
    assert len(inventory["services"]) == 46
    assert len(inventory["unmatched"]) == 6
    assert inventory["roadmap"]["waves"]
    assert client.get(f"/assessments/{assessment['id']}").json()["inventory"] == inventory


def test_dora_hints_follow_the_questionnaire(seeded):
    assessment = create()
    upload(assessment["id"])

    open_case = client.get(f"/assessments/{assessment['id']}").json()["inventory"]["dora_hints"]
    bank = put_answers(assessment["id"], {"sector": "KREDITINSTITUT"}).json()
    other = put_answers(assessment["id"], {"sector": "ANDERER"}).json()

    assert (open_case["applies"], len(open_case["hints"])) == (None, 3)
    assert bank["inventory"]["dora_hints"]["applies"] is True
    assert bank["inventory"]["dora_hints"]["condition"] == "DORA gilt laut Fragebogen."
    assert (
        other["inventory"]["dora_hints"]["applies"],
        other["inventory"]["dora_hints"]["hints"],
    ) == (
        False,
        [],
    )


def test_new_inventory_replaces_the_old_one(seeded, session):
    assessment = create()
    upload(assessment["id"])

    body = upload(assessment["id"], csv("Slack;Chat;gering;nein;nein"), "neu.csv").json()

    rows = session.query(InventoryMatch).filter_by(assessment_id=assessment["id"]).all()
    assert [(row.row, row.service_slug) for row in rows] == [(2, "slack")]
    assert body["inventory"]["inventory"]["name"] == "neu.csv"
    assert [service["service"] for service in body["inventory"]["services"]] == ["slack"]


def test_invalid_inventory_is_rejected_and_nothing_is_stored(seeded):
    assessment = create()

    response = upload(assessment["id"], csv("Slack;Chat;sehr hoch;nein;nein"), "fehler.csv")

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["row"] == 2
    assert client.get(f"/assessments/{assessment['id']}").json()["inventory"] is None


def test_unsupported_file_type_is_rejected():
    assessment = create()

    assert upload(assessment["id"], b"x", "bestand.pdf").status_code == 415


def test_inventory_for_unknown_assessment_gives_404():
    assert upload(999999).status_code == 404


class CountingClassifier:
    """Schlägt immer Slack vor und zählt, wie oft es gefragt wird."""

    def __init__(self):
        self.calls = 0

    def choose(self, entry, catalog):
        self.calls += 1
        return AiChoice("slack", 0.7, "Testvorschlag")


def test_ai_matches_are_stored_and_not_requested_again(seeded):
    classifier = CountingClassifier()
    app.dependency_overrides[get_classifier] = lambda: classifier
    assessment = create()

    body = upload(assessment["id"], csv("Teamchat intern;Chat;gering;nein;nein"), "b.csv").json()
    calls_after_upload = classifier.calls
    client.get(f"/assessments/{assessment['id']}")
    put_answers(assessment["id"], {"sector": "ANDERER"})

    service = body["inventory"]["services"][0]
    assert (service["service"], service["needs_review"]) == ("slack", True)
    assert calls_after_upload == 1
    assert classifier.calls == 1


def test_match_to_a_vanished_service_is_reported_as_open(seeded, session):
    assessment = create()
    upload(assessment["id"], csv("Slack;Chat;gering;nein;nein"), "b.csv")
    session.query(InventoryMatch).filter_by(assessment_id=assessment["id"]).update(
        {"service_slug": "gibt-es-nicht"}
    )

    body = client.get(f"/assessments/{assessment['id']}").json()

    assert body["inventory"]["services"] == []
    assert "gibt-es-nicht" in body["inventory"]["unmatched"][0]["reason"]


# ---------------------------------------------------------------- Übergabe aus dem Schnellcheck

FROM_SCAN = {
    "name": "Testbank AG",
    "domain": "https://www.testbank.de/",
    "services": ["microsoft-365", "cloudflare", "microsoft-365"],
    "sector": {
        "value": "KREDITINSTITUT",
        "label": "Kreditinstitut",
        "quote": "Wir sind eine Direktbank",
    },
    "employees": {"value": 1200, "label": "1.200", "quote": "Rund 1.200 Mitarbeitende"},
    "profile": {"legal_name": "Testbank AG", "lei": "3KXUNHVVQFIJN6RHLO76", "supervision": True},
}


def test_assessment_from_scan_keeps_suggestions_apart_from_answers(seeded):
    response = client.post("/assessments/from-scan", json=FROM_SCAN)

    body = response.json()
    assert response.status_code == 201
    assert (body["name"], body["domain"]) == ("Testbank AG", "testbank.de")
    assert body["answers"] == {}  # Vorschläge sind keine Antworten
    assert body["prefill"]["sector"]["value"] == "KREDITINSTITUT"
    assert body["prefill"]["employees"]["value"] == 1200
    assert body["prefill"]["profile"]["lei"] == "3KXUNHVVQFIJN6RHLO76"


def test_scanned_services_become_the_starter_inventory(seeded, session):
    body = client.post("/assessments/from-scan", json=FROM_SCAN).json()

    services = {service["service"] for service in body["inventory"]["services"]}
    rows = session.query(InventoryMatch).filter_by(assessment_id=body["id"]).all()
    assert services == {"microsoft-365", "cloudflare"}
    assert len(rows) == 2  # doppelte Dienste nur einmal
    assert all(row.method.value == "TEXT" for row in rows)
    assert body["inventory"]["inventory"]["name"] == "Außenscan testbank.de.csv"


def test_from_scan_without_services_has_no_inventory(seeded):
    body = client.post("/assessments/from-scan", json={**FROM_SCAN, "services": []}).json()

    assert body["inventory"] is None


@pytest.mark.parametrize(
    ("change", "location"),
    [
        ({"services": ["gibt-es-nicht"]}, "services"),
        ({"sector": {"value": "MOND", "label": "x", "quote": "y"}}, "sector"),
        ({"employees": {"value": -5, "label": "x", "quote": "y"}}, "employees"),
    ],
)
def test_invalid_scan_data_is_rejected(seeded, change, location):
    response = client.post("/assessments/from-scan", json={**FROM_SCAN, **change})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["location"] == location


def test_from_scan_rejects_internal_domains(seeded):
    response = client.post("/assessments/from-scan", json={**FROM_SCAN, "domain": "localhost"})

    assert response.json()["error"]["code"] == "INVALID_DOMAIN"


def test_report_of_a_stored_assessment_has_summary_risks_and_sources(seeded):
    assessment = create()
    upload(assessment["id"])

    body = client.get(f"/assessments/{assessment['id']}/report").json()

    report = body["report"]
    assert body["assessment"]["name"] == "Musterbank AG"
    assert report["headline"].endswith("unterliegen dem Recht eines Staates außerhalb der EU.")
    assert 0 < report["outside_eu"] <= report["assessed"]
    assert len(report["top_risks"]) == 3
    assert all(risk["criticality"] == "HOCH" for risk in report["top_risks"])
    assert report["sources"] and all(source["services"] for source in report["sources"])


def test_report_needs_an_inventory(seeded):
    assessment = create()

    response = client.get(f"/assessments/{assessment['id']}/report")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVENTORY_MISSING"


def test_report_of_the_sample_bank_needs_no_stored_assessment(seeded):
    body = client.get("/assessments/demo/report").json()

    assert body["assessment"]["name"] == "Musterbank AG"
    assert body["report"]["assessed"] > 40
    assert "offen" in body["report"]["regulation"]
