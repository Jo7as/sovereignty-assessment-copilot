"""Tiefenprüfung: Verträge lesen. Ablauf und Regeln in docs/tiefenpruefung-ablauf.md.

Schritt 1 (Aufnehmen): Text Seite für Seite. Seite meint immer die physische Seite im PDF,
gezählt ab 1, nicht die aufgedruckte Seitenzahl. Nur so lässt sich ein Zitat der KI später
automatisch auf seiner Seite wiederfinden.
"""

import io
import logging
from enum import StrEnum

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_PAGES = 300
# Weniger Zeichen auf einer Seite gelten als „ohne Text“, etwa nur eine Seitenzahl
MIN_PAGE_TEXT = 20

# pypdf meldet fehlende Schriftdetails, die für den Text keine Rolle spielen
logging.getLogger("pypdf").setLevel(logging.ERROR)


class DocumentType(StrEnum):
    """Dokumenttypen für das Routing (Arbeitsanweisung 5.2)."""

    AVV = "AVV"
    RAHMENVERTRAG = "RAHMENVERTRAG"
    LEISTUNGSBESCHREIBUNG = "LEISTUNGSBESCHREIBUNG"
    STANDARDVERTRAGSKLAUSELN = "STANDARDVERTRAGSKLAUSELN"
    UNTERAUFTRAGNEHMER = "UNTERAUFTRAGNEHMER"
    SONSTIGES = "SONSTIGES"


class UnreadablePdf(Exception):
    """Die Datei ist kein lesbares PDF."""


def read_pages(content: bytes) -> list[str]:
    """Text je Seite. Seiten ohne Text ergeben einen leeren Text."""
    try:
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) > MAX_PAGES:
            raise UnreadablePdf(f"Das PDF hat mehr als {MAX_PAGES} Seiten.")
        # Nullzeichen kommen in manchen PDFs vor, die Datenbank lehnt sie ab
        pages = [(page.extract_text() or "").replace("\x00", "") for page in reader.pages]
    except (PyPdfError, ValueError, KeyError, TypeError) as problem:
        raise UnreadablePdf("Die Datei ist kein lesbares PDF.") from problem
    return [page if len(page.strip()) >= MIN_PAGE_TEXT else "" for page in pages]


def pages_without_text(pages: list[str]) -> list[int]:
    """Seitennummern (ab 1) ohne Text, etwa gescannte Seiten."""
    return [number for number, text in enumerate(pages, 1) if not text]
