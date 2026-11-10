"""Belegprüfung: Steht ein Zitat der KI wörtlich im Quelltext?

Gemeinsam für die Vorschläge im Schnellcheck und die Vertragsanalyse
(docs/tiefenpruefung-ablauf.md, Abschnitt 5.4).
"""

import re

MIN_QUOTE = 10  # Zeichen; kürzere Zitate belegen nichts


def squeeze(text: str) -> str:
    """Vergleichsform: ohne Leerraum, Abschnittstrenner und Trennstriche.

    PDFs trennen Wörter am Zeilenende („Verarbei-“ / „tung“), und die Textauslese setzt
    manchmal Leerzeichen mitten in Wörter („becom e“). Deshalb zählen Leerraum, Bindestriche
    und weiche Trennstriche beim Vergleich gar nicht. Die Buchstaben müssen trotzdem alle und
    in derselben Reihenfolge im Text stehen.
    """
    text = text.replace("­", "").replace("-", "").replace("|", "")
    return "".join(text.split())


def is_quoted(quote: str, text: str, minimum: int = MIN_QUOTE) -> bool:
    """Steht das Zitat wörtlich im Text? Leerraum, Trennstriche und Trenner zählen nicht.

    `minimum` nur senken, wenn der Code das Zitat zusätzlich prüft, etwa auf einen Namen.
    """
    quote = squeeze(quote)
    return len(quote) >= minimum and quote in squeeze(text)


def numbers(text: str) -> set[int]:
    """Ganze Zahlen im Text, auch mit Tausenderpunkt oder -leerzeichen: „340.000“ → 340000."""
    return {
        int(re.sub(r"[.\s ]", "", number))
        for number in re.findall(r"\d{1,3}(?:[.\s ]\d{3})+|\d+", text)
    }
