"""API-Endpunkt: den Fragebogen laden."""

from fastapi import APIRouter

from app.questionnaire import load_questionnaire

questionnaire_router = APIRouter(prefix="/questionnaire", tags=["Fragebogen"])


@questionnaire_router.get("")
def get_questionnaire() -> dict:
    """Alle Fragen mit Antworten, Stufen und Rechtsgrundlagen."""
    return load_questionnaire().model_dump(mode="json")
