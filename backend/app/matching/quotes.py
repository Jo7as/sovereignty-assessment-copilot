"""Belegprüfung: Steht ein Zitat der KI wörtlich im Quelltext?

Gemeinsam für die Vorschläge im Schnellcheck und die Vertragsanalyse
(docs/tiefenpruefung-ablauf.md, Abschnitt 5.4).
"""

import re

MIN_QUOTE = 10  # Zeichen; kürzere Zitate belegen nichts


def squeeze(text: str) -> str:
    """Vergleichsform: ohne Leerraum-Unterschiede, Abschnittstrenner und Trennstriche.

    PDFs trennen Wörter am Zeilenende („Verarbei-“ / „tung“). Deshalb fällt erst der Umbruch
    nach einem Bindestrich weg, danach zählen Bindestriche und weiche Trennstriche gar nicht.
    So passen „Verarbeitung“ und „IT-Sicherheit“ auch über einen Zeilenumbruch hinweg.
    """
    text = re.sub(r"-[ \t]*\r?\n\s*", "-", text)
    text = text.replace("­", "").replace("-", "").replace("|", " ")
    return " ".join(text.split())


def is_quoted(quote: str, text: str) -> bool:
    """Steht das Zitat wörtlich im Text? Leerraum, Trennstriche und Trenner zählen nicht."""
    quote = squeeze(quote)
    return len(quote) >= MIN_QUOTE and quote in squeeze(text)


def numbers(text: str) -> set[int]:
    """Ganze Zahlen im Text, auch mit Tausenderpunkt oder -leerzeichen: „340.000“ → 340000."""
    return {
        int(re.sub(r"[.\s ]", "", number))
        for number in re.findall(r"\d{1,3}(?:[.\s ]\d{3})+|\d+", text)
    }
