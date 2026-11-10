"""API-Endpunkte für Verträge am Assessment: hochladen, einordnen, auslesen, Ergebnisse.

Ablauf nach docs/tiefenpruefung-ablauf.md: Beim Hochladen schlägt die KI Dokumenttyp und
Dienst vor (Schritt 2), der Berater bestätigt beides, erst dann startet der Lauf (Schritte 3
bis 5) im Hintergrund.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.assessment.stored_api import load_assessment
from app.config import settings
from app.contracts import DocumentType, UnreadablePdf, pages_without_text, read_pages
from app.contracts.pipeline import Extractor, OpenRouterExtractor, classify
from app.contracts.runs import (
    SessionFactory,
    classification_log,
    execute_run,
    is_active,
    latest,
    run_summary,
    service_results,
    start_run,
)
from app.db import get_session, get_session_factory
from app.inventory.api import error
from app.matching.catalog import load_catalog
from app.models import Assessment, AssessmentContract

# Verträge mit Anlagen sind größer als ein IT-Bestand
MAX_FILE_SIZE = 20 * 1024 * 1024

contracts_router = APIRouter(prefix="/assessments", tags=["Verträge"])


def get_extractor() -> Extractor | None:
    """Die KI für die Vertragsanalyse. Ohne Schlüssel gibt es keine."""
    if not settings.openrouter_api_key:
        return None
    return OpenRouterExtractor(settings.openrouter_api_key, settings.openrouter_model)


class ContractUpdate(BaseModel):
    """Einordnung durch den Berater (Arbeitsanweisung 5.2)."""

    document_type: DocumentType
    service: str = Field(min_length=1, max_length=80)


@contracts_router.post("/{assessment_id:int}/contracts", status_code=status.HTTP_201_CREATED)
async def upload_contract(
    assessment_id: int,
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
    extractor: Annotated[Extractor | None, Depends(get_extractor)],
) -> dict:
    """Speichert ein Vertragsdokument und seinen Text Seite für Seite.

    Ohne Text auf irgendeiner Seite (etwa ein Scan) wird nichts gespeichert, denn ohne Text
    kann nichts ausgelesen und kein Zitat geprüft werden (Arbeitsanweisung, Abschnitt 7).
    Mit KI kommt ein Vorschlag für Dokumenttyp und Dienst dazu, nach zwei bis drei Sekunden.
    """
    assessment = load_assessment(session, assessment_id)
    name = file.filename or "Vertrag.pdf"
    if not name.lower().endswith(".pdf"):
        raise error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "UNSUPPORTED_FILE_TYPE",
            "Erlaubt sind Verträge im Format .pdf.",
        )
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "FILE_TOO_LARGE",
            f"Die Datei ist größer als {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )
    try:
        # Lesen dauert bei langen Verträgen Sekunden, der Server soll derweil weiter antworten
        pages = await run_in_threadpool(read_pages, content)
    except UnreadablePdf as problem:
        raise error(status.HTTP_400_BAD_REQUEST, "UNREADABLE_FILE", str(problem)) from problem
    if not any(pages):
        raise error(
            422,
            "NO_TEXT",
            "Das PDF enthält keinen Text, vermutlich ein Scan. Bitte ein PDF mit Text hochladen.",
        )
    contract = AssessmentContract(filename=name, content=content, pages=pages)
    if extractor is not None:
        services = _inventory_services(assessment)
        candidates = [item for item in load_catalog(session) if item.slug in services]
        result = await run_in_threadpool(classify, extractor, pages, candidates)
        contract.classification = classification_log(result, settings.openrouter_model)
    assessment.contracts.append(contract)
    session.commit()
    return _summary(contract)


@contracts_router.get("/{assessment_id:int}/contracts")
def list_contracts(assessment_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Alle Verträge mit Einordnung und Stand des jüngsten Laufs. Die Oberfläche fragt hier
    ab, ob ein Lauf fertig ist."""
    assessment = load_assessment(session, assessment_id)
    return {"contracts": [_summary(contract) for contract in assessment.contracts]}


@contracts_router.put("/{assessment_id:int}/contracts/{contract_id:int}")
def update_contract(
    assessment_id: int,
    contract_id: int,
    body: ContractUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Der Berater bestätigt oder ändert Dokumenttyp und Dienst."""
    assessment = load_assessment(session, assessment_id)
    contract = _load_contract(session, assessment_id, contract_id)
    if body.service not in _inventory_services(assessment):
        raise error(
            422,
            "SERVICE_NOT_IN_INVENTORY",
            f"Der Dienst „{body.service}“ steht nicht im IT-Bestand. Bitte zuerst dort ergänzen.",
        )
    if is_active(latest(contract)):
        raise error(
            409, "RUN_ACTIVE", "Während eines Laufs lässt sich die Einordnung nicht ändern."
        )
    contract.document_type, contract.service_slug = body.document_type, body.service
    session.commit()
    return _summary(contract)


@contracts_router.post(
    "/{assessment_id:int}/contracts/{contract_id:int}/runs",
    status_code=status.HTTP_202_ACCEPTED,
)
def start_contract_run(
    assessment_id: int,
    contract_id: int,
    background: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
    extractor: Annotated[Extractor | None, Depends(get_extractor)],
    open_session: Annotated[SessionFactory, Depends(get_session_factory)],
) -> dict:
    """Startet die Vertragsanalyse im Hintergrund und antwortet sofort."""
    contract = _load_contract(session, assessment_id, contract_id)
    if extractor is None:
        raise error(503, "AI_UNAVAILABLE", "Für die Vertragsanalyse ist keine KI eingerichtet.")
    if contract.document_type is None or contract.service_slug is None:
        raise error(
            409,
            "NOT_CLASSIFIED",
            "Bitte zuerst Dokumenttyp und Dienst bestätigen (Arbeitsanweisung 5.2).",
        )
    if is_active(latest(contract)):
        raise error(409, "RUN_ACTIVE", "Für diesen Vertrag läuft schon eine Analyse.")
    run = start_run(contract, settings.openrouter_model)
    session.commit()
    background.add_task(execute_run, run.id, open_session, extractor)
    return _summary(contract)


@contracts_router.get("/{assessment_id:int}/contracts/results")
def contract_results(assessment_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Je Dienst eine Angabe pro Feld, Widersprüche als UNKLAR, mit allen Fundstellen."""
    return {"services": service_results(load_assessment(session, assessment_id))}


@contracts_router.delete(
    "/{assessment_id:int}/contracts/{contract_id:int}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_contract(
    assessment_id: int, contract_id: int, session: Annotated[Session, Depends(get_session)]
) -> Response:
    contract = _load_contract(session, assessment_id, contract_id)
    session.delete(contract)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _load_contract(session: Session, assessment_id: int, contract_id: int) -> AssessmentContract:
    contract = session.get(AssessmentContract, contract_id)
    if contract is None or contract.assessment_id != assessment_id:
        raise error(404, "CONTRACT_NOT_FOUND", f"Vertrag {contract_id} gibt es hier nicht.")
    return contract


def _inventory_services(assessment: Assessment) -> set[str]:
    """Dienste, denen der IT-Bestand des Assessments zugeordnet ist."""
    return {match.service_slug for match in assessment.matches if match.service_slug}


def _summary(contract: AssessmentContract) -> dict:
    """Überblick ohne den Text der Seiten, der kann lang sein."""
    return {
        "id": contract.id,
        "filename": contract.filename,
        "page_count": len(contract.pages),
        "pages_without_text": pages_without_text(contract.pages),
        "service": contract.service_slug,
        "document_type": contract.document_type,
        "classification": contract.classification,
        "run": run_summary(latest(contract)),
        "uploaded_at": contract.created_at.isoformat(),
    }
