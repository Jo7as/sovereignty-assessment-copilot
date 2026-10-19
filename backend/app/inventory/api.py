"""API-Endpunkt für den Import eines IT-Bestands."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.db import get_session
from app.inventory.importer import ImportResult, UnreadableFile, read_inventory
from app.matching import Classifier, match_entry
from app.matching.catalog import default_classifier, load_catalog

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB reichen für Tausende Zeilen

router = APIRouter(prefix="/inventory", tags=["IT-Bestand"])


def error(status_code: int, code: str, message: str, details: list | None = None) -> HTTPException:
    body = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return HTTPException(status_code, detail=body)


TEMPLATE = PROJECT_ROOT / "data" / "templates" / "it-bestand-vorlage.xlsx"


@router.get("/template")
def download_template() -> FileResponse:
    """Die Excel-Vorlage für den IT-Bestand."""
    return FileResponse(
        TEMPLATE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=TEMPLATE.name,
    )


def get_classifier() -> Classifier | None:
    return default_classifier()


async def read_upload(file: UploadFile) -> ImportResult:
    """Prüft Dateityp und Größe und liest den IT-Bestand. Gemeinsam für Import und Bewertung."""
    _, result = await receive_upload(file)
    return result


def raise_if_invalid(inventory: ImportResult) -> None:
    """Fehler im Bestand verhindern die Bewertung, damit kein Ergebnis auf unvollständigen
    Daten entsteht. Alle Fehler kommen auf einmal, jeweils mit Zeile und Spalte."""
    if inventory.errors:
        raise error(
            422,
            "INVALID_INVENTORY",
            f"Der IT-Bestand enthält {len(inventory.errors)} Fehler. "
            "Bitte korrigieren und erneut hochladen.",
            details=[
                {"row": problem.row, "column": problem.column, "message": problem.message}
                for problem in inventory.errors
            ],
        )


async def receive_upload(file: UploadFile) -> tuple[bytes, ImportResult]:
    """Wie read_upload, gibt zusätzlich den Inhalt der Datei zurück, etwa zum Speichern."""
    name = file.filename or ""
    if not name.lower().endswith((".xlsx", ".csv")):
        raise error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "UNSUPPORTED_FILE_TYPE",
            "Erlaubt sind Dateien im Format .xlsx oder .csv.",
        )
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise error(
            status.HTTP_413_CONTENT_TOO_LARGE, "FILE_TOO_LARGE", "Die Datei ist größer als 5 MB."
        )
    try:
        return content, read_inventory(content, name)
    except UnreadableFile as problem:
        raise error(status.HTTP_400_BAD_REQUEST, "UNREADABLE_FILE", str(problem)) from problem


@router.post("/import")
async def import_inventory(
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
    classifier: Annotated[Classifier | None, Depends(get_classifier)],
) -> dict:
    """Liest den IT-Bestand, meldet alle Fehler auf einmal und ordnet jeden Eintrag einem
    Dienst zu. Unsichere Zuordnungen sind als zur Prüfung markiert. Gespeichert wird noch nichts."""
    result = await read_upload(file)
    catalog = load_catalog(session)
    entries = []
    for entry in result.entries:
        match = match_entry(entry.values, catalog, classifier)
        entries.append(
            {
                "row": entry.row,
                **{key: _json(value) for key, value in entry.values.items()},
                "match": {
                    "service": match.slug,
                    "method": match.method,
                    "confidence": round(match.confidence, 2),
                    "reason": match.reason,
                    "needs_review": match.needs_review,
                },
            }
        )
    return {
        "valid": not result.errors,
        "entries": entries,
        "needs_review": sum(entry["match"]["needs_review"] for entry in entries),
        "errors": [
            {"row": problem.row, "column": problem.column, "message": problem.message}
            for problem in result.errors
        ],
        "warnings": result.warnings,
    }


def _json(value: object) -> object:
    # Wertelisten sind Text-Enums und werden von selbst zu Text, Datumswerte nicht
    return value.isoformat() if isinstance(value, date) else value
