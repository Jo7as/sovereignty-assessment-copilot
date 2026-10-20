"""Vorschläge der KI für Branche und Beschäftigte, aus dem Text der Website.

Die KI muss jeden Vorschlag mit einem wörtlichen Zitat belegen. Das Zitat wird geprüft:
Steht es nicht so im Text, wird der Vorschlag verworfen. Bei den Beschäftigten muss die Zahl
im Zitat vorkommen. Vorschläge bleiben Vorschläge, ein Mensch bestätigt sie im Fragebogen.
"""

import json
import re
from dataclasses import dataclass
from typing import Protocol

from app.matching.ai import chat

MAX_TEXT = 12_000  # Zeichen Website-Text, die an die KI gehen

PROMPT = """Du liest den Text der Website eines Unternehmens und schlägst Angaben
für einen Fragebogen vor.

Erlaubte Branchen (Wert: Bezeichnung):
{sectors}

Text der Website:
\"\"\"
{text}
\"\"\"

Regeln:
- Wähle die Branche nur aus der Liste. Passt keine sicher, setze null.
- Die Zahl der Beschäftigten nur, wenn der Text sie ausdrücklich nennt. Sonst null.
- Belege jede Angabe mit einem wörtlichen Zitat aus dem Text, höchstens 200 Zeichen,
  genau so geschrieben wie im Text.

Antworte nur mit JSON:
{{"sector": "WERT oder null", "sector_quote": "...",
 "employees": 123 oder null, "employees_quote": "..."}}"""


@dataclass(frozen=True)
class Suggestion:
    value: str | int
    label: str
    quote: str  # geprüft: steht so im Text der Website


@dataclass
class Suggestions:
    sector: Suggestion | None = None
    employees: Suggestion | None = None
    note: str | None = None


class Suggester(Protocol):
    def ask(self, prompt: str) -> str: ...


class OpenRouterSuggester:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key, self.model = api_key, model

    def ask(self, prompt: str) -> str:
        return chat(self.api_key, self.model, prompt)


def suggest(text: str, sectors: dict[str, str], suggester: Suggester) -> Suggestions:
    """Fragt die KI und behält nur Vorschläge mit überprüfbarem Zitat."""
    text = text[:MAX_TEXT]
    if not text.strip():
        return Suggestions(note="Die Website enthielt keinen auswertbaren Text.")
    options = "\n".join(f"{value}: {label}" for value, label in sectors.items())
    try:
        answer = suggester.ask(PROMPT.format(sectors=options, text=text))
    except Exception:  # noqa: BLE001 - ohne KI gibt es eben keine Vorschläge
        return Suggestions(note="Die KI war nicht erreichbar, es gibt keine Vorschläge.")
    data = _json(answer)
    result = Suggestions()
    sector, sector_quote = data.get("sector"), str(data.get("sector_quote") or "")
    if isinstance(sector, str) and sector in sectors and _quoted(sector_quote, text):
        result.sector = Suggestion(sector, sectors[sector], sector_quote.strip())
    employees, employees_quote = data.get("employees"), str(data.get("employees_quote") or "")
    if (
        isinstance(employees, int)
        and not isinstance(employees, bool)
        and employees > 0
        and _quoted(employees_quote, text)
        and employees in _numbers(employees_quote)
    ):
        result.employees = Suggestion(
            employees, f"{employees:,}".replace(",", "."), employees_quote.strip()
        )
    return result


def _json(text: str) -> dict:
    found = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        data = json.loads(found.group(0)) if found else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _squeeze(text: str) -> str:
    return " ".join(text.replace("|", " ").split())


def _quoted(quote: str, text: str) -> bool:
    """Steht das Zitat wörtlich im Text? Leerraum und Abschnittstrenner zählen nicht."""
    quote = _squeeze(quote)
    return len(quote) >= 10 and quote in _squeeze(text)


def _numbers(text: str) -> set[int]:
    """Ganze Zahlen im Text, auch mit Tausenderpunkt oder -leerzeichen: „340.000“ → 340000."""
    return {
        int(re.sub(r"[.\s ]", "", number))
        for number in re.findall(r"\d{1,3}(?:[.\s ]\d{3})+|\d+", text)
    }
