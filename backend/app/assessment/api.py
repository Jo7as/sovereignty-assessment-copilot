"""API-Endpunkt: IT-Bestand hochladen und bewerten lassen."""

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.assessment import AssessedService, assess_inventory
from app.db import get_session
from app.inventory.api import error, get_classifier, read_upload
from app.matching import Classifier
from app.roadmap import WAVE_TITLES, build_roadmap
from app.scoring import Finding, ObjectiveResult

router = APIRouter(prefix="/assessments", tags=["Bewertung"])


@router.post("/preview")
async def preview_assessment(
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
    classifier: Annotated[Classifier | None, Depends(get_classifier)],
) -> dict:
    """Bewertet einen IT-Bestand, ohne etwas zu speichern. Fehler im Bestand verhindern die
    Bewertung, damit kein Ergebnis auf unvollständigen Daten entsteht."""
    inventory = await read_upload(file)
    if inventory.errors:
        raise error(
            422, "INVALID_INVENTORY", "Der IT-Bestand enthält Fehler. Zuerst den Import prüfen."
        )
    today = date.today()
    result = assess_inventory(inventory.entries, session, today, classifier)
    portfolio = result.portfolio
    roadmap = build_roadmap(result, session, today)
    return {
        "services": [_service(service) for service in result.services],
        "unmatched": [
            {"row": entry.row, "service": entry.service, "reason": entry.match.reason}
            for entry in result.unmatched
        ],
        "portfolio": None
        if portfolio is None
        else {
            "level": round(portfolio.level, 2),
            "potential": round(portfolio.potential, 2),
            "score": round(portfolio.score, 1),
            "potential_score": round(portfolio.potential_score, 1),
            "levels": {k: round(v, 2) for k, v in portfolio.levels.items()},
            "weakest_critical_level": portfolio.weakest_critical_level,
            "weakest_critical_services": list(portfolio.weakest_critical_services),
            "distribution": portfolio.distribution,
            "provisional_services": portfolio.provisional_services,
        },
        "roadmap": {
            "waves": [
                {
                    "wave": wave,
                    "title": WAVE_TITLES[wave],
                    "items": [asdict(item) for item in items],
                }
                for wave, items in roadmap.waves.items()
            ],
            "measures": [asdict(measure) for measure in roadmap.measures],
            "questions": [asdict(question) for question in roadmap.questions],
        },
    }


def _service(service: AssessedService) -> dict:
    assessment = service.assessment
    return {
        "service": service.slug,
        "name": service.name,
        "variant": service.variant_slug,
        "criticality": service.criticality,
        "critical_function": service.critical_function,
        "rows": list(service.rows),
        "needs_review": service.needs_review,
        "level": assessment.level,
        "potential": assessment.potential,
        "score": round(assessment.score, 1),
        "potential_score": round(assessment.potential_score, 1),
        "gaps": list(assessment.gaps),
        "objectives": {
            objective: _objective(result) for objective, result in assessment.objectives.items()
        },
        "notes": list(service.notes),
    }


def _objective(result: ObjectiveResult) -> dict:
    return {
        "level": result.level,
        "potential": result.potential,
        "findings": [_finding(finding) for finding in result.findings],
    }


def _finding(finding: Finding) -> dict:
    return {**asdict(finding), "is_gap": finding.is_gap}
