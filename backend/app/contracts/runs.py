"""Läufe der Vertragsanalyse: im Hintergrund ausführen, speichern, zusammenfassen.

Ein Lauf dauert Minuten, weil jeder Themenblock jeden Abschnitt des Vertrags einzeln liest.
Deshalb startet die API ihn und antwortet sofort, die Oberfläche fragt den Stand ab.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.contracts import DocumentType, FindingStatus, RunStatus
from app.contracts.fields import FIELDS, fields_for_type
from app.contracts.pipeline import (
    PROMPT_VERSION,
    BlockResult,
    ClassificationResult,
    Extractor,
    MergedField,
    merge,
)
from app.contracts.pipeline import extract as extract_all
from app.models import Assessment, AssessmentContract, ContractFinding, ContractRun

# Gleichzeitige Anfragen an die KI je Lauf. Mehr bringt wenig, Ratenlimits werden wahrscheinlicher.
WORKERS = 4
# Ein Lauf, der so lange „läuft“, ist abgebrochen, etwa weil der Server neu gestartet wurde
STALE_AFTER = timedelta(minutes=30)

type SessionFactory = Callable[[], AbstractContextManager[Session]]


def start_run(contract: AssessmentContract, model: str) -> ContractRun:
    run = ContractRun(status=RunStatus.LAEUFT, prompt_version=PROMPT_VERSION, model=model, log={})
    contract.runs.append(run)
    return run


def execute_run(run_id: int, open_session: SessionFactory, extractor: Extractor) -> None:
    """Liest den Vertrag aus und speichert Angaben und Protokoll.

    Die Datenbanksitzung ist nur zum Laden und Speichern offen, nicht während der Minuten,
    in denen die KI arbeitet.
    """
    with open_session() as session:
        run = session.get(ContractRun, run_id)
        pages, document_type = run.contract.pages, run.contract.document_type
    try:
        blocks = extract_all(extractor, pages, DocumentType(document_type), WORKERS)
        failure = None
    except Exception as error:  # noqa: BLE001 - der Lauf endet mit Fehler statt hängenzubleiben
        blocks, failure = [], f"Lauf abgebrochen: {error}"
    with open_session() as session:
        run = session.get(ContractRun, run_id)
        run.log = {"blocks": [_block_log(block) for block in blocks]}
        if failure:
            run.log["error"] = failure
        run.findings = [
            ContractFinding(
                field=item.field,
                value=item.value,
                quote=item.quote,
                page=item.page,
                status=FindingStatus.KI_VORSCHLAG,
            )
            for block in blocks
            for item in block.accepted
        ]
        failed = failure is not None or (blocks and all(block.error for block in blocks))
        run.status = RunStatus.FEHLER if failed else RunStatus.FERTIG
        run.finished_at = datetime.now(UTC)
        session.commit()


def _block_log(block: BlockResult) -> dict:
    return {
        "block": block.block.value,
        "seconds": block.seconds,
        "error": block.error,
        "answers": block.answers,
        "rejected": [
            {
                "field": item.evidence.field,
                "value": item.evidence.value,
                "quote": item.evidence.quote,
                "page": item.evidence.page,
                "reason": item.reason.name,
            }
            for item in block.rejected
        ],
    }


def is_active(run: ContractRun | None) -> bool:
    return (
        run is not None
        and run.status == RunStatus.LAEUFT
        and datetime.now(UTC) - run.created_at < STALE_AFTER
    )


def latest(contract: AssessmentContract, status: RunStatus | None = None) -> ContractRun | None:
    runs = [run for run in contract.runs if status is None or run.status == status]
    return runs[-1] if runs else None


def run_summary(run: ContractRun | None) -> dict | None:
    """Stand eines Laufs für die Oberfläche, ohne die rohen Antworten der KI."""
    if run is None:
        return None
    blocks = run.log.get("blocks", [])
    errors = [f"{block['block']}: {block['error']}" for block in blocks if block["error"]]
    if run.log.get("error"):
        errors.append(run.log["error"])
    status = run.status
    if status == RunStatus.LAEUFT and not is_active(run):
        status = RunStatus.FEHLER
        errors.append("Lauf abgebrochen, bitte neu starten.")
    finished = run.finished_at
    return {
        "id": run.id,
        "status": status,
        "prompt_version": run.prompt_version,
        "model": run.model,
        "started_at": run.created_at.isoformat(),
        "finished_at": finished.isoformat() if finished else None,
        "seconds": round((finished - run.created_at).total_seconds()) if finished else None,
        "findings": len(run.findings),
        "rejected": sum(len(block["rejected"]) for block in blocks),
        "errors": errors,
    }


def classification_log(result: ClassificationResult, model: str) -> dict:
    return {
        "document_type": result.document_type,
        "service": result.service,
        "quote": result.quote,
        "page": result.page,
        "note": result.note,
        "seconds": result.seconds,
        "prompt_version": PROMPT_VERSION,
        "model": model,
    }


def service_results(assessment: Assessment) -> list[dict]:
    """Je Dienst eine Angabe pro Feld, über alle seine Verträge (Arbeitsanweisung 5.5).

    Grundlage ist je Vertrag der jüngste fertige Lauf. Verworfene Angaben zählen nicht.
    """
    by_service: dict[str, list[tuple[AssessmentContract, ContractRun]]] = {}
    for contract in assessment.contracts:
        run = latest(contract, RunStatus.FERTIG)
        if run and contract.service_slug and contract.document_type:
            by_service.setdefault(contract.service_slug, []).append((contract, run))
    results = []
    for service, documents in by_service.items():
        document_types = [DocumentType(contract.document_type) for contract, _ in documents]
        read = {item.name for kind in document_types for item in fields_for_type(kind)}
        findings = [
            finding
            for _, run in documents
            for finding in run.findings
            if finding.status != FindingStatus.VERWORFEN
        ]
        fields = [item.name for item in FIELDS if item.name in read]
        results.append(
            {
                "service": service,
                "contracts": [contract.id for contract, _ in documents],
                "fields": [
                    _field_json(merged) for merged in merge(fields, findings, document_types)
                ],
            }
        )
    return results


def _field_json(merged: MergedField[ContractFinding]) -> dict:
    return {
        "field": merged.field,
        "state": merged.state,
        "value": merged.value,
        "findings": [_finding_json(finding) for finding in merged.findings],
        # Bei Prüfpunkten: welcher Bestandteil belegt ist, fehlt oder nicht geprüft wurde
        "elements": [
            {
                "element": item.element.name,
                "question": item.element.question,
                "kind": item.element.kind.name,
                "state": item.state,
                "finding_ids": [finding.id for finding in item.findings],
            }
            for item in merged.elements
        ],
    }


def _finding_json(finding: ContractFinding) -> dict:
    return {
        "id": finding.id,
        "contract_id": finding.run.contract_id,
        "filename": finding.run.contract.filename,
        "field": finding.field,
        "value": finding.value,
        "quote": finding.quote,
        "page": finding.page,
        "status": finding.status,
    }
