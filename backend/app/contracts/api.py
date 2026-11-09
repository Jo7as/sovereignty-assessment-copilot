"""API-Endpunkte für Verträge am Assessment: hochladen, auflisten, löschen."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.assessment.stored_api import load_assessment
from app.contracts import UnreadablePdf, pages_without_text, read_pages
from app.db import get_session
from app.inventory.api import error
from app.models import AssessmentContract

# Verträge mit Anlagen sind größer als ein IT-Bestand
MAX_FILE_SIZE = 20 * 1024 * 1024

contracts_router = APIRouter(prefix="/assessments", tags=["Verträge"])


@contracts_router.post("/{assessment_id:int}/contracts", status_code=status.HTTP_201_CREATED)
async def upload_contract(
    assessment_id: int, file: UploadFile, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Speichert ein Vertragsdokument und seinen Text Seite für Seite.

    Ohne Text auf irgendeiner Seite (etwa ein Scan) wird nichts gespeichert, denn ohne Text
    kann nichts ausgelesen und kein Zitat geprüft werden (Arbeitsanweisung, Abschnitt 7).
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
    assessment.contracts.append(contract)
    session.commit()
    return _summary(contract)


@contracts_router.get("/{assessment_id:int}/contracts")
def list_contracts(assessment_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    assessment = load_assessment(session, assessment_id)
    return {"contracts": [_summary(contract) for contract in assessment.contracts]}


@contracts_router.delete(
    "/{assessment_id:int}/contracts/{contract_id:int}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_contract(
    assessment_id: int, contract_id: int, session: Annotated[Session, Depends(get_session)]
) -> Response:
    contract = session.get(AssessmentContract, contract_id)
    if contract is None or contract.assessment_id != assessment_id:
        raise error(404, "CONTRACT_NOT_FOUND", f"Vertrag {contract_id} gibt es hier nicht.")
    session.delete(contract)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _summary(contract: AssessmentContract) -> dict:
    """Überblick ohne den Text der Seiten, der kann lang sein."""
    return {
        "id": contract.id,
        "filename": contract.filename,
        "page_count": len(contract.pages),
        "pages_without_text": pages_without_text(contract.pages),
        "service": contract.service_slug,
        "document_type": contract.document_type,
        "uploaded_at": contract.created_at.isoformat(),
    }
