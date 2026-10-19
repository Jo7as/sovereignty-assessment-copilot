"""Stufe 1 der Zuordnung: Textvergleich ohne KI.

Ein Eintrag gilt als zugeordnet, wenn er
- einen Namen oder eine Schreibweise des Dienstes als ganze Wortfolge enthält,
- sie mit kleinen Tippfehlern enthält oder
- ein Markenwort enthält, das nur bei genau einem Dienst vorkommt.
Zugeordnet wird nur bei deutlichem Abstand zum zweitbesten Dienst.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from rapidfuzz.fuzz import ratio

THRESHOLD = 85  # ab diesem Wert gilt ein Treffer als sicher
MARGIN = 5  # so viel Abstand braucht der beste Dienst zum zweitbesten
EXACT, UNIQUE_BRAND = 95, 88
MIN_FUZZY_RATIO = 85  # Ähnlichkeit je Wort, damit ein Tippfehler noch zählt

# Allgemeine Wörter. Sie bleiben im Vergleich erhalten („Google Cloud“ bleibt zwei Wörter),
# gelten aber nie als Markenwort
NOISE = frozenset(
    {
        "and", "cloud", "de", "der", "die", "das", "for", "fur", "gmbh", "inc", "limited",
        "lizenz", "lizenzen", "ltd", "online", "platform", "plattform", "plc", "se", "service",
        "services", "software", "the", "und", "corporation", "ag", "co", "kg", "sa", "sarl",
    }
)  # fmt: skip


@dataclass(frozen=True)
class CatalogService:
    slug: str
    name: str
    aliases: tuple[str, ...] = ()
    provider: str = ""


@dataclass(frozen=True)
class TextMatch:
    slug: str | None
    score: float
    candidates: tuple[tuple[str, float], ...]  # beste Dienste mit Wert, absteigend


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def match_text(entry_text: str, catalog: list[CatalogService]) -> TextMatch:
    entry = tokens(entry_text)
    if not entry:
        return TextMatch(None, 0, ())
    frequency = _brand_frequency(catalog)
    scores = {
        service.slug: max(
            (_score(entry, candidate, frequency) for candidate in _candidates(service)),
            default=0,
        )
        for service in catalog
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_slug, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    accepted = best >= THRESHOLD and best - second >= MARGIN
    return TextMatch(best_slug if accepted else None, best, tuple(ranked[:5]))


def _candidates(service: CatalogService) -> list[list[str]]:
    texts = [service.name, *service.aliases]
    return [candidate for candidate in (tokens(text) for text in texts) if candidate]


def _brand_frequency(catalog: list[CatalogService]) -> Counter:
    """In wie vielen Diensten kommt ein Wort vor? Ein Wort aus nur einem Dienst ist eine Marke."""
    counts = Counter()
    for service in catalog:
        words = {word for candidate in _candidates(service) for word in candidate}
        words |= set(tokens(service.provider))
        counts.update(words - NOISE)
    return counts


def _score(entry: list[str], candidate: list[str], frequency: Counter) -> float:
    if _contains_phrase(entry, candidate):
        return EXACT
    fuzzy = _fuzzy_phrase(entry, candidate)
    unique_brand = any(
        word in entry and frequency[word] == 1 and len(word) >= 3 and word not in NOISE
        for word in candidate
    )
    return max(fuzzy, UNIQUE_BRAND if unique_brand else 0)


def _contains_phrase(entry: list[str], candidate: list[str]) -> bool:
    size = len(candidate)
    return any(entry[start : start + size] == candidate for start in range(len(entry) - size + 1))


def _fuzzy_phrase(entry: list[str], candidate: list[str]) -> float:
    """Jedes Wort des Kandidaten braucht ein ähnliches Wort im Eintrag. Kurze Wörter und Zahlen
    müssen exakt stimmen, sonst würde „365“ zu „360“ oder „g“ zu „go“."""
    similarities = []
    for word in candidate:
        if len(word) <= 3 or word.isdigit():
            similarity = 100 if word in entry else 0
        else:
            similarity = max(ratio(word, other) for other in entry)
        if similarity < MIN_FUZZY_RATIO:
            return 0
        similarities.append(similarity)
    return 0.95 * sum(similarities) / len(similarities)
