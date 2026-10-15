"""API-Endpunkt für den Import eines IT-Bestands."""

from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.inventory.importer import UnreadableFile, read_inventory

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB reichen für Tausende Zeilen

router = APIRouter(prefix="/inventory", tags=["IT-Bestand"])


def error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code, detail={"code": code, "message": message})


@router.post("/import")
async def import_inventory(file: UploadFile) -> dict:
    """Liest den IT-Bestand und meldet alle Fehler auf einmal. Gespeichert wird noch nichts."""
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
        result = read_inventory(content, name)
    except UnreadableFile as problem:
        raise error(status.HTTP_400_BAD_REQUEST, "UNREADABLE_FILE", str(problem)) from problem

    return {
        "valid": not result.errors,
        "entries": [
            {"row": entry.row, **{key: _json(value) for key, value in entry.values.items()}}
            for entry in result.entries
        ],
        "errors": [
            {"row": problem.row, "column": problem.column, "message": problem.message}
            for problem in result.errors
        ],
        "warnings": result.warnings,
    }


def _json(value: object) -> object:
    # Wertelisten sind Text-Enums und werden von selbst zu Text, Datumswerte nicht
    return value.isoformat() if isinstance(value, date) else value
