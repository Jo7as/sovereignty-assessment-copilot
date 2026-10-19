"""Bewertung eines IT-Bestands: von den Einträgen zur Heatmap und zum Gesamtwert.

Mehrere Einträge zum selben Dienst (etwa O365, Teams und Exchange) werden zusammengefasst.
Der Dienst zählt einmal, mit der höchsten genannten Kritikalität. Sonst würde ein Anbieter
durch Mehrfachnennung übergewichtet.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.inventory import InventoryEntry
from app.matching import Classifier, MatchResult, Method, match_entry
from app.matching.catalog import load_catalog
from app.matching.text import tokens
from app.models import Criticality, Service, ServiceVariant
from app.scoring import (
    CRITICALITY_WEIGHT,
    PortfolioAssessment,
    PortfolioItem,
    ServiceAssessment,
    assess_portfolio,
    assess_variant,
)

# Wörter, die in Variantenbezeichnungen nichts unterscheiden
VARIANT_STOPWORDS = frozenset({"mit", "ohne", "und", "fur", "der", "die", "das", "von", "im", "in"})


@dataclass(frozen=True)
class AssessedService:
    slug: str
    name: str
    variant_slug: str
    variant_name: str
    criticality: Criticality
    critical_function: bool
    rows: tuple[int, ...]  # Zeilen im IT-Bestand, die zu diesem Dienst gehören
    needs_review: bool  # mindestens eine Zuordnung ist ein ungeprüfter Vorschlag
    assessment: ServiceAssessment
    notes: tuple[str, ...]


@dataclass(frozen=True)
class UnmatchedEntry:
    row: int
    service: str
    match: MatchResult


@dataclass(frozen=True)
class InventoryAssessment:
    services: tuple[AssessedService, ...]
    unmatched: tuple[UnmatchedEntry, ...]
    portfolio: PortfolioAssessment | None


def assess_inventory(
    entries: Sequence[InventoryEntry],
    session: Session,
    today: date,
    classifier: Classifier | None = None,
) -> InventoryAssessment:
    catalog = load_catalog(session)
    grouped: dict[str, list[tuple[InventoryEntry, MatchResult]]] = defaultdict(list)
    unmatched = []
    for entry in entries:
        match = match_entry(entry.values, catalog, classifier)
        if match.slug is None:
            unmatched.append(UnmatchedEntry(entry.row, entry.service, match))
        else:
            grouped[match.slug].append((entry, match))

    services = [_assess_service(session, slug, items, today) for slug, items in grouped.items()]
    services.sort(
        key=lambda s: (-CRITICALITY_WEIGHT[s.criticality], s.assessment.level, s.name.casefold())
    )
    portfolio = (
        assess_portfolio([PortfolioItem(s.name, s.criticality, s.assessment) for s in services])
        if services
        else None
    )
    return InventoryAssessment(tuple(services), tuple(unmatched), portfolio)


def _assess_service(
    session: Session, slug: str, items: list[tuple[InventoryEntry, MatchResult]], today: date
) -> AssessedService:
    service = session.scalars(select(Service).where(Service.slug == slug)).one()
    variant_texts = sorted({str(e.values["variant"]) for e, _ in items if e.values.get("variant")})
    variant, notes = _choose_variant(service, variant_texts)
    return AssessedService(
        slug=service.slug,
        name=service.name,
        variant_slug=variant.slug,
        variant_name=variant.name,
        criticality=max((e.criticality for e, _ in items), key=CRITICALITY_WEIGHT.__getitem__),
        critical_function=any(e.critical_function for e, _ in items),
        rows=tuple(e.row for e, _ in items),
        needs_review=any(match.method is not Method.TEXT for _, match in items),
        assessment=assess_variant(variant, today),
        notes=tuple(notes),
    )


def _choose_variant(service: Service, variant_texts: list[str]) -> tuple[ServiceVariant, list[str]]:
    """Wählt die Variante, deren Name ein unterscheidendes Wort mit der Angabe im Bestand teilt."""
    default = next(variant for variant in service.variants if variant.is_default)
    if not variant_texts:
        return default, []
    words = {
        variant.slug: set(tokens(variant.name)) - VARIANT_STOPWORDS for variant in service.variants
    }
    for text in variant_texts:
        wanted = set(tokens(text)) - VARIANT_STOPWORDS
        hits = [
            variant
            for variant in service.variants
            if any(
                word in words[variant.slug] and sum(word in other for other in words.values()) == 1
                for word in wanted
            )
        ]
        if len(hits) == 1:
            return hits[0], []
    joined = ", ".join(f"„{text}“" for text in variant_texts)
    return default, [f"Variante {joined} nicht erkannt, bewertet wird „{default.name}“."]


__all__ = ["AssessedService", "InventoryAssessment", "UnmatchedEntry", "assess_inventory"]
