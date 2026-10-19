"""API-Endpunkt: IT-Bestand hochladen und bewerten lassen."""

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessment import AssessedService, InventoryAssessment, assess_inventory
from app.compliance import as_json, inventory_hints
from app.config import PROJECT_ROOT
from app.db import get_session
from app.inventory import InventoryEntry, read_inventory
from app.inventory.api import error, get_classifier, read_upload
from app.matching import Classifier
from app.models import Evidence, Organization, Service, ServiceVariant
from app.roadmap import WAVE_TITLES, build_roadmap
from app.scoring import Finding, ObjectiveResult

router = APIRouter(prefix="/assessments", tags=["Bewertung"])


MUSTERBANK = PROJECT_ROOT / "data" / "testdata" / "musterbank-it-bestand.xlsx"


@router.get("/demo")
def demo_assessment(session: Annotated[Session, Depends(get_session)]) -> dict:
    """Bewertet die fiktive Musterbank AG. Ohne KI, damit die Demo bei jedem Aufruf gleich ist."""
    inventory = read_inventory(MUSTERBANK.read_bytes(), MUSTERBANK.name)
    return _response("Musterbank AG", inventory.entries, session, classifier=None)


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
            422,
            "INVALID_INVENTORY",
            f"Der IT-Bestand enthält {len(inventory.errors)} Fehler. "
            "Bitte korrigieren und erneut hochladen.",
            details=[
                {"row": problem.row, "column": problem.column, "message": problem.message}
                for problem in inventory.errors
            ],
        )
    return _response(file.filename or "IT-Bestand", inventory.entries, session, classifier)


def _response(
    name: str,
    entries: list[InventoryEntry],
    session: Session,
    classifier: Classifier | None,
) -> dict:
    today = date.today()
    result: InventoryAssessment = assess_inventory(entries, session, today, classifier)
    portfolio = result.portfolio
    roadmap = build_roadmap(result, session, today)
    return {
        "inventory": {"name": name, "entries": len(entries), "assessed_on": today.isoformat()},
        "services": [_service(service, session) for service in result.services],
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
                {"wave": wave, "title": WAVE_TITLES[wave], "items": [asdict(i) for i in items]}
                for wave, items in roadmap.waves.items()
            ],
            "measures": [asdict(measure) for measure in roadmap.measures],
            "questions": [asdict(question) for question in roadmap.questions],
        },
        "dora_hints": {
            "condition": "Gilt, wenn das Unternehmen ein Finanzunternehmen im Sinne von "
            "Art. 2 DORA ist. Das klärt der Fragebogen.",
            "hints": as_json(inventory_hints(result.services)),
        },
    }


def _evidence(session: Session, service: AssessedService) -> list[dict]:
    """Belege der bewerteten Variante und der beteiligten Unternehmen."""
    variant = _variant(session, service)
    organizations: list[Organization] = [variant.service.provider]
    if variant.operator is not None:
        organizations.append(variant.operator)
    rows = list(variant.evidence) + [
        item
        for organization in organizations
        for item in session.scalars(
            select(Evidence).where(Evidence.organization_id == organization.id)
        )
    ]
    return [
        {
            "attribute": item.attribute,
            "source_url": item.source_url,
            "quote": item.quote,
            "retrieved_at": item.retrieved_at.isoformat(),
        }
        for item in rows
    ]


def _service(service: AssessedService, session: Session) -> dict:
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
        "provider": service.provider,
        "variant_name": service.variant_name,
        "review_status": _review_status(session, service),
        "evidence": _evidence(session, service),
    }


def _review_status(session: Session, service: AssessedService) -> str:
    return _variant(session, service).review_status


def _variant(session: Session, service: AssessedService) -> ServiceVariant:
    return session.scalars(
        select(ServiceVariant)
        .join(Service)
        .where(Service.slug == service.slug, ServiceVariant.slug == service.variant_slug)
    ).one()


def _objective(result: ObjectiveResult) -> dict:
    return {
        "level": result.level,
        "potential": result.potential,
        "findings": [_finding(finding) for finding in result.findings],
    }


def _finding(finding: Finding) -> dict:
    return {**asdict(finding), "is_gap": finding.is_gap}
