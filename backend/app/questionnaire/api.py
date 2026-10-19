"""API-Endpunkte: Fragebogen laden, Assessments anlegen und Antworten speichern."""

from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.compliance import as_json, determine_regulation, question_hints
from app.db import get_session
from app.inventory.api import error
from app.models import Assessment, AssessmentAnswer
from app.questionnaire import load_questionnaire
from app.questionnaire.answers import AnswerValue, check_answers, maturity

questionnaire_router = APIRouter(prefix="/questionnaire", tags=["Fragebogen"])
assessments_router = APIRouter(prefix="/assessments", tags=["Assessments"])


class AssessmentCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class AnswersUpdate(BaseModel):
    # Die Werte prüft check_answers gegen den Fragebogen, damit alle Fehler auf einmal kommen
    answers: dict[str, Any] = Field(min_length=1)


@questionnaire_router.get("")
def get_questionnaire() -> dict:
    """Alle Fragen mit Antworten, Stufen und Rechtsgrundlagen."""
    return load_questionnaire().model_dump(mode="json")


@assessments_router.post("", status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: AssessmentCreate, session: Annotated[Session, Depends(get_session)]
) -> dict:
    assessment = Assessment(name=body.name, questionnaire_version=load_questionnaire().version)
    session.add(assessment)
    session.commit()
    return _response(assessment)


# Der Pfad nimmt nur Zahlen an, damit /assessments/demo nicht hier landet
@assessments_router.get("/{assessment_id:int}")
def get_assessment(assessment_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    return _response(_load(session, assessment_id))


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
    return _response(assessment)


def _load(session: Session, assessment_id: int) -> Assessment:
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        raise error(404, "ASSESSMENT_NOT_FOUND", f"Assessment {assessment_id} gibt es nicht.")
    return assessment


def _response(assessment: Assessment) -> dict:
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
    }


def _json(value: AnswerValue) -> str | int | float:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value
