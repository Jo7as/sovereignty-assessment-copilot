"""Baut den Katalog für die Zuordnung aus der Anbieterdatenbank."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.matching.ai import Classifier, OpenRouterClassifier
from app.matching.text import CatalogService
from app.models import Service


def load_catalog(session: Session) -> list[CatalogService]:
    services = session.scalars(select(Service).order_by(Service.slug)).all()
    return [
        CatalogService(
            slug=service.slug,
            name=service.name,
            aliases=tuple(alias.alias for alias in service.aliases),
            provider=service.provider.name,
        )
        for service in services
    ]


def default_classifier() -> Classifier | None:
    """Die KI-Stufe ist nur aktiv, wenn ein Schlüssel hinterlegt ist."""
    if not settings.openrouter_api_key:
        return None
    return OpenRouterClassifier(settings.openrouter_api_key, settings.openrouter_model)
