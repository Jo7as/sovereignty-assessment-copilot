"""Zuordnung eines Eintrags aus dem IT-Bestand zu einem Dienst der Anbieterdatenbank."""

from dataclasses import dataclass
from enum import StrEnum

from app.matching.ai import AiChoice, Classifier
from app.matching.text import CatalogService, match_text, normalize


class Method(StrEnum):
    TEXT = "TEXT"  # sicherer Textvergleich
    AI = "AI"  # Vorschlag der KI, muss geprüft werden
    NONE = "NONE"  # kein Dienst gefunden, muss geprüft werden


@dataclass(frozen=True)
class MatchResult:
    slug: str | None
    method: Method
    confidence: float
    reason: str

    @property
    def needs_review(self) -> bool:
        return self.method is not Method.TEXT


def match_entry(
    entry: dict[str, object],
    catalog: list[CatalogService],
    classifier: Classifier | None = None,
) -> MatchResult:
    text = str(entry.get("service", ""))
    found = match_text(text, catalog)
    if found.slug is None and entry.get("provider"):
        # Hilft bei allgemeinen Bezeichnungen wie „WAN“, wenn der Vertragspartner genannt ist
        found = match_text(f"{text} {entry['provider']}", catalog)
    if found.slug is not None:
        return MatchResult(
            found.slug, Method.TEXT, found.score / 100, f"Textvergleich mit „{text}“."
        )

    if classifier is None:
        return MatchResult(None, Method.NONE, 0, "Kein sicherer Treffer im Textvergleich.")
    choice = classifier.choose(entry, catalog)
    known = {service.slug for service in catalog}
    if choice.slug is not None and choice.slug not in known:
        return MatchResult(None, Method.AI, 0, "Die KI nannte einen Dienst, den es nicht gibt.")
    return MatchResult(choice.slug, Method.AI, choice.confidence, choice.reason)


__all__ = [
    "AiChoice",
    "CatalogService",
    "Classifier",
    "MatchResult",
    "Method",
    "match_entry",
    "normalize",
]
