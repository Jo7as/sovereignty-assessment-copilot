"""Vertragsanalyse über die API: einordnen, bestätigen, Lauf im Hintergrund, Ergebnisse.

Arbeitsanweisung docs/tiefenpruefung-ablauf.md, Schritte 2 bis 5 und Abschnitt 8 (Protokoll).
Die KI ist durch eine Attrappe ersetzt. Der TestClient führt Hintergrundaufgaben aus, bevor
er die Antwort zurückgibt, deshalb ist ein Lauf im Test sofort fertig.
"""

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.contracts import FindingStatus, RunStatus
from app.contracts import api as contracts_api
from app.contracts.api import get_extractor
from app.contracts.pipeline import (
    PROMPT_VERSION,
    BlockAnswer,
    Classification,
    ElementFinding,
    Finding,
)
from app.contracts.runs import execute_run, start_run
from app.db import get_session, get_session_factory
from app.main import app
from app.matching import Method
from app.matching.ai import InvalidAnswer
from app.matching.text import CatalogService
from app.models import Assessment, AssessmentContract, ContractFinding, ContractRun, InventoryMatch
from tests.test_contracts_api import make_pdf

client = TestClient(app)

AVV = make_pdf(
    "Data Processing Addendum for Example Storage provided by Example Cloud GmbH",
    "Customer Data will be stored exclusively in data centres within the European Union.",
)
SAME = "stored exclusively in data centres within the European Union"


class FakeExtractor:
    """Antwortet je nach Schritt und Themenblock. Ohne Reihenfolge, weil der Lauf die
    Anfragen gleichzeitig stellt."""

    def __init__(self, findings=None, fail=False, elements=()):
        self.findings = (
            findings
            if findings is not None
            else [
                Finding(field="data_location", value="EU_ZUGESICHERT", quote=SAME, page=2),
                Finding(field="data_location", value="EU_ZUGESICHERT", quote="Frankfurt", page=2),
            ]
        )
        self.fail = fail
        self.elements = list(elements)  # Bestandteile, gemeldet im Block der DSGVO-Prüfliste

    def ask(self, prompt, answer):
        if answer is Classification:
            return Classification(
                document_type="AVV",
                service="example-storage",
                quote="Example Storage provided by Example Cloud GmbH",
                page=1,
            )
        if self.fail:
            raise InvalidAnswer("findings: Field required")
        if "„DSGVO-Prüfliste“" in prompt:
            return BlockAnswer(findings=[], elements=self.elements)
        return BlockAnswer(findings=self.findings if "„Datenort“" in prompt else [])


@pytest.fixture(autouse=True)
def database(session, monkeypatch):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_session_factory] = lambda: lambda: nullcontext(session)
    app.dependency_overrides[get_extractor] = FakeExtractor
    monkeypatch.setattr(
        contracts_api,
        "load_catalog",
        lambda session: [
            CatalogService("example-storage", "Example Storage", provider="Example Cloud GmbH")
        ],
    )
    yield
    app.dependency_overrides.clear()


def create(session, services=("example-storage",)) -> int:
    assessment_id = client.post("/assessments", json={"name": "Musterbank AG"}).json()["id"]
    assessment = session.get(Assessment, assessment_id)
    for row, slug in enumerate(services, 1):
        assessment.matches.append(
            InventoryMatch(row=row, service_slug=slug, method=Method.TEXT, confidence=1, reason="")
        )
    session.commit()
    return assessment_id


def upload(assessment_id: int, content: bytes = AVV, name: str = "avv.pdf") -> dict:
    return client.post(
        f"/assessments/{assessment_id}/contracts",
        files={"file": (name, content, "application/pdf")},
    ).json()


def confirm(assessment_id: int, contract_id: int, service="example-storage", kind="AVV"):
    return client.put(
        f"/assessments/{assessment_id}/contracts/{contract_id}",
        json={"document_type": kind, "service": service},
    )


def run(assessment_id: int, contract_id: int):
    return client.post(f"/assessments/{assessment_id}/contracts/{contract_id}/runs")


def ready(session, content: bytes = AVV, name: str = "avv.pdf") -> tuple[int, int]:
    """Assessment mit einem hochgeladenen und bestätigten Vertrag."""
    assessment_id = create(session)
    contract_id = upload(assessment_id, content, name)["id"]
    confirm(assessment_id, contract_id)
    return assessment_id, contract_id


# ---------------------------------------------------------------- Einordnen und bestätigen


def test_upload_stores_the_classification_proposal_with_evidence(session):
    contract = upload(create(session))

    proposal = contract["classification"]
    assert proposal["document_type"] == "AVV"
    assert proposal["service"] == "example-storage"
    assert proposal["page"] == 1 and proposal["note"] is None
    assert proposal["prompt_version"] == PROMPT_VERSION
    # Ein Vorschlag ist noch keine Einordnung
    assert contract["document_type"] is None and contract["service"] is None


def test_consultant_confirms_type_and_service(session):
    assessment_id = create(session)
    contract_id = upload(assessment_id)["id"]

    response = confirm(assessment_id, contract_id)

    assert response.status_code == 200
    assert response.json()["document_type"] == "AVV"
    assert response.json()["service"] == "example-storage"


def test_service_must_be_in_the_inventory(session):
    assessment_id = create(session)
    contract_id = upload(assessment_id)["id"]

    response = confirm(assessment_id, contract_id, service="salesforce")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SERVICE_NOT_IN_INVENTORY"


def test_unknown_document_type_is_rejected(session):
    assessment_id = create(session)
    contract_id = upload(assessment_id)["id"]

    assert confirm(assessment_id, contract_id, kind="VERTRAG").status_code == 422


# ---------------------------------------------------------------- Lauf


def test_run_needs_a_confirmed_classification(session):
    assessment_id = create(session)
    contract_id = upload(assessment_id)["id"]

    response = run(assessment_id, contract_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_CLASSIFIED"


def test_run_needs_an_ai(session):
    assessment_id, contract_id = ready(session)
    app.dependency_overrides[get_extractor] = lambda: None

    response = run(assessment_id, contract_id)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_UNAVAILABLE"


def test_run_stores_checked_findings_and_a_protocol(session):
    assessment_id, contract_id = ready(session)

    response = run(assessment_id, contract_id)

    assert response.status_code == 202
    assert response.json()["run"]["status"] == "LAEUFT"  # Antwort vor dem Lauf
    (contract,) = client.get(f"/assessments/{assessment_id}/contracts").json()["contracts"]
    summary = contract["run"]
    assert summary["status"] == "FERTIG"
    assert (summary["findings"], summary["rejected"], summary["errors"]) == (1, 1, [])
    assert summary["model"] and summary["prompt_version"] == PROMPT_VERSION
    stored = session.get(ContractRun, summary["id"])
    (finding,) = stored.findings
    assert (finding.field, finding.value, finding.page) == ("data_location", "EU_ZUGESICHERT", 2)
    assert finding.status == FindingStatus.KI_VORSCHLAG
    datenort = next(block for block in stored.log["blocks"] if block["block"] == "Datenort")
    assert len(datenort["answers"]) == 1  # rohe, geprüfte Antwort der KI
    assert datenort["rejected"][0]["reason"] == "ZITAT"


def test_run_where_every_block_fails_ends_with_error(session):
    assessment_id, contract_id = ready(session)
    app.dependency_overrides[get_extractor] = lambda: FakeExtractor(fail=True)

    run(assessment_id, contract_id)

    (contract,) = client.get(f"/assessments/{assessment_id}/contracts").json()["contracts"]
    assert contract["run"]["status"] == "FEHLER"
    assert "Datenort: Abschnitt 1 von 1 nicht ausgelesen" in contract["run"]["errors"][0]


def test_unexpected_error_ends_the_run_instead_of_leaving_it_running(session):
    assessment_id, contract_id = ready(session)

    class Broken:
        def ask(self, prompt, answer):
            raise RuntimeError("kaputt")

    run_id = session.get(ContractRun, _start(session, contract_id)).id
    execute_run(run_id, lambda: nullcontext(session), Broken())

    stored = session.get(ContractRun, run_id)
    assert stored.status == RunStatus.FEHLER
    assert stored.log["error"] == "Lauf abgebrochen: kaputt"


def _start(session, contract_id: int) -> int:
    started = start_run(session.get(AssessmentContract, contract_id), "test-model")
    session.commit()
    return started.id


def test_second_run_while_one_is_running_is_refused(session):
    assessment_id, contract_id = ready(session)
    _start(session, contract_id)

    response = run(assessment_id, contract_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RUN_ACTIVE"
    assert confirm(assessment_id, contract_id).status_code == 409


def test_stale_run_counts_as_aborted_and_can_be_restarted(session):
    assessment_id, contract_id = ready(session)
    stale = session.get(ContractRun, _start(session, contract_id))
    stale.created_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    (contract,) = client.get(f"/assessments/{assessment_id}/contracts").json()["contracts"]

    assert contract["run"]["status"] == "FEHLER"
    assert contract["run"]["errors"] == ["Lauf abgebrochen, bitte neu starten."]
    assert run(assessment_id, contract_id).status_code == 202


# ---------------------------------------------------------------- Zusammenführen


def results(assessment_id: int) -> dict:
    (service,) = client.get(f"/assessments/{assessment_id}/contracts/results").json()["services"]
    return {field["field"]: field for field in service["fields"]}


def test_results_merge_per_service_and_report_not_found(session):
    assessment_id, contract_id = ready(session)
    run(assessment_id, contract_id)

    fields = results(assessment_id)

    assert fields["data_location"]["state"] == "GEFUNDEN"
    assert fields["data_location"]["value"] == "EU_ZUGESICHERT"
    assert fields["data_location"]["findings"][0]["filename"] == "avv.pdf"
    assert fields["dsgvo_28_3_a"]["state"] == "NICHT_GEFUNDEN"
    assert "governing_law" not in fields  # gehört nicht zu den Blöcken eines AVV


def test_contradiction_between_documents_is_unclear(session):
    assessment_id, first = ready(session)
    run(assessment_id, first)
    second = upload(assessment_id, name="anlage.pdf")["id"]
    confirm(assessment_id, second)
    selectable = Finding(field="data_location", value="EU_WAEHLBAR", quote=SAME, page=2)
    app.dependency_overrides[get_extractor] = lambda: FakeExtractor([selectable])
    run(assessment_id, second)

    field = results(assessment_id)["data_location"]

    assert field["state"] == "UNKLAR" and field["value"] is None
    assert [item["filename"] for item in field["findings"]] == ["avv.pdf", "anlage.pdf"]


def test_discarded_findings_do_not_count(session):
    assessment_id, contract_id = ready(session)
    run(assessment_id, contract_id)
    for finding in session.query(ContractFinding):
        finding.status = FindingStatus.VERWORFEN
    session.commit()

    assert results(assessment_id)["data_location"]["state"] == "NICHT_GEFUNDEN"


def test_results_without_finished_runs_are_empty(session):
    assessment_id = create(session)
    upload(assessment_id)

    response = client.get(f"/assessments/{assessment_id}/contracts/results")

    assert response.json() == {"services": []}


def test_check_is_judged_from_its_elements_and_shows_which_are_missing(session):
    pdf = make_pdf(
        "Data Processing Addendum for Example Storage provided by Example Cloud GmbH",
        "Upon termination the Processor shall delete all Customer Data without undue delay.",
    )
    assessment_id, contract_id = ready(session, pdf)
    deletion = ElementFinding(
        element="dsgvo_28_3_g.loeschung", quote="shall delete all Customer Data", page=2
    )
    app.dependency_overrides[get_extractor] = lambda: FakeExtractor([], elements=[deletion])
    run(assessment_id, contract_id)

    field = results(assessment_id)["dsgvo_28_3_g"]

    assert (field["state"], field["value"]) == ("GEFUNDEN", "TEILWEISE")
    states = {item["element"]: item["state"] for item in field["elements"]}
    assert states == {
        "dsgvo_28_3_g.rueckgabe": "NICHT_BELEGT",
        "dsgvo_28_3_g.loeschung": "BELEGT",
    }
    assert field["findings"][0]["field"] == "dsgvo_28_3_g.loeschung"
    assert field["elements"][1]["finding_ids"] == [field["findings"][0]["id"]]
