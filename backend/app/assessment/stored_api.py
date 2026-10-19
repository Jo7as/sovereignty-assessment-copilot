"""API-Endpunkte für gespeicherte Assessments: anlegen, Antworten und IT-Bestand speichern,
Gesamtergebnis abrufen."""

from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, UploadFile, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.assessment.api import inventory_result
from app.compliance import Regulation, as_json, determine_regulation, question_hints
from app.db import get_session
from app.inventory import read_inventory
from app.inventory.api import error, get_classifier, raise_if_invalid, receive_upload
from app.matching import Classifier, MatchResult, match_entry
from app.matching.catalog import load_catalog
from app.models import Assessment, AssessmentAnswer, AssessmentInventory, InventoryMatch
from app.questionnaire import load_questionnaire
from app.questionnaire.answers import AnswerValue, check_answers, maturity

assessments_router = APIRouter(prefix="/assessments", tags=["Assessments"])


class AssessmentCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class AnswersUpdate(BaseModel):
    # Die Werte prüft check_answers gegen den Fragebogen, damit alle Fehler auf einmal kommen
    answers: dict[str, Any] = Field(min_length=1)


@assessments_router.post("", status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: AssessmentCreate, session: Annotated[Session, Depends(get_session)]
) -> dict:
    assessment = Assessment(name=body.name, questionnaire_version=load_questionnaire().version)
    session.add(assessment)
    session.commit()
    return _response(assessment, session)


# Der Pfad nimmt nur Zahlen an, damit /assessments/demo nicht hier landet
@assessments_router.get("/{assessment_id:int}")
def get_assessment(assessment_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    return _response(_load(session, assessment_id), session)


@assessments_router.put("/{assessment_id:int}/answers")
def update_answers(
    assessment_id: int, body: AnswersUpdate, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Speichert Antworten, auch nur einen Teil davon. `null` löscht eine Antwort.
    Ist eine Antwort ungültig, wird nichts gespeichert."""
    assessment = _load(session, assessment_id)
    checked, problems = check_answers(load_questionnaire(), body.answers)
    if problems:
        raise error(
            422,
            "INVALID_ANSWERS",
            f"{len(problems)} {'Antwort ist' if len(problems) == 1 else 'Antworten sind'} "
            "ungültig. Es wurde nichts gespeichert.",
            details=[asdict(problem) for problem in problems],
        )
    stored = {answer.question_key: answer for answer in assessment.answers}
    for key, value in checked.items():
        if value is None:
            if key in stored:
                assessment.answers.remove(stored[key])
            continue
        answer = stored.get(key) or AssessmentAnswer(question_key=key)
        answer.option_value, answer.number_value = (
            (None, value) if isinstance(value, Decimal) else (value, None)
        )
        if key not in stored:
            assessment.answers.append(answer)
    session.commit()
    session.refresh(assessment)
    return _response(assessment, session)


@assessments_router.put("/{assessment_id:int}/inventory")
async def upload_inventory(
    assessment_id: int,
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
    classifier: Annotated[Classifier | None, Depends(get_classifier)],
) -> dict:
    """Speichert den IT-Bestand und seine Zuordnung. Ein neuer Bestand ersetzt den alten.

    Die Zuordnung wird hier einmal berechnet, auch mit KI, und gespeichert. Die Bewertung
    entsteht bei jedem Abruf neu, mit dem aktuellen Stand der Anbieterdatenbank.
    """
    assessment = _load(session, assessment_id)
    content, inventory = await receive_upload(file)
    raise_if_invalid(inventory)
    catalog = load_catalog(session)
    stored = assessment.inventory or AssessmentInventory()
    stored.filename, stored.content = file.filename or "IT-Bestand", content
    assessment.inventory = stored
    assessment.matches.clear()
    session.flush()  # alte Zuordnungen löschen, bevor neue mit denselben Zeilen entstehen
    for entry in inventory.entries:
        match = match_entry(entry.values, catalog, classifier)
        assessment.matches.append(
            InventoryMatch(
                row=entry.row,
                service_slug=match.slug,
                method=match.method,
                confidence=match.confidence,
                reason=match.reason,
            )
        )
    session.commit()
    session.refresh(assessment)
    return _response(assessment, session)


def _load(session: Session, assessment_id: int) -> Assessment:
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        raise error(404, "ASSESSMENT_NOT_FOUND", f"Assessment {assessment_id} gibt es nicht.")
    return assessment


def _response(assessment: Assessment, session: Session) -> dict:
    questionnaire = load_questionnaire()
    answers: dict[str, AnswerValue] = {
        answer.question_key: (
            answer.option_value if answer.option_value is not None else answer.number_value
        )
        for answer in assessment.answers
    }
    # Antworten auf Fragen, die eine neuere Fassung des Fragebogens nicht mehr kennt, zählen nicht
    known = {question.key for question in questionnaire.questions}
    regulation = determine_regulation(questionnaire, answers)
    hints, unanswered = question_hints(questionnaire, answers, regulation)
    return {
        "id": assessment.id,
        "name": assessment.name,
        "questionnaire_version": assessment.questionnaire_version,
        "created_at": assessment.created_at.isoformat(),
        "updated_at": assessment.updated_at.isoformat(),
        "answers": {key: _json(value) for key, value in answers.items()},
        "progress": {
            "answered": len(known & answers.keys()),
            "total": len(known),
        },
        "maturity": asdict(maturity(questionnaire, answers)),
        "regulation": {
            **as_json(regulation),
            "applicable_laws": sorted(regulation.applicable_laws),
            "hints": as_json(hints),
            "unanswered_obligations": unanswered,
        },
        "inventory": _inventory(assessment, session, regulation),
    }


def _inventory(assessment: Assessment, session: Session, regulation: Regulation) -> dict | None:
    """Bewertung des gespeicherten IT-Bestands mit den gespeicherten Zuordnungen."""
    stored = assessment.inventory
    if stored is None:
        return None
    entries = read_inventory(stored.content, stored.filename).entries
    matches = {
        match.row: MatchResult(match.service_slug, match.method, match.confidence, match.reason)
        for match in assessment.matches
    }
    result = inventory_result(
        stored.filename, entries, session, matches=matches, regulation=regulation
    )
    result["inventory"]["uploaded_at"] = stored.updated_at.isoformat()
    return result


def _json(value: AnswerValue) -> str | int | float:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value
