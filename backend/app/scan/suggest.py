"""Vorschläge der KI für Branche und Beschäftigte, aus dem Text der Website.

Die KI muss jeden Vorschlag mit einem wörtlichen Zitat belegen. Das Zitat wird geprüft:
Steht es nicht so im Text, wird der Vorschlag verworfen. Bei den Beschäftigten muss die Zahl
im Zitat vorkommen. Vorschläge bleiben Vorschläge, ein Mensch bestätigt sie im Fragebogen.
"""

import json
import queue
import re
import threading
from dataclasses import dataclass
from typing import Protocol

from app.matching.ai import chat

MAX_TEXT = 12_000  # Zeichen Website-Text, die an die KI gehen
# Kurzes Nachdenken. Gemessen am 23.10.2026 mit siemens.com: Manche Anbieter halten sich daran
# (5 statt 9 bis 13 Sekunden), andere ignorieren es und denken 2.000 bis 6.000 Tokens lang
# (8 bis 22 Sekunden). Ganz ohne Nachdenken antwortet das Modell in 1 bis 2 Sekunden, schwankt
# aber bei der Branche, etwa bei Capgemini zwischen „Beratung“ und „IKT-Dienste“.
REASONING = {"effort": "low"}
# Gesamtfrist für die Antwort in Sekunden. Die Frist von httpx gilt nur zwischen zwei
# Datenpaketen, und OpenRouter schickt beim Nachdenken laufend Lebenszeichen.
DEADLINE = 45

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
    pending: bool = False  # Die KI wird noch gefragt, die Vorschläge folgen


class Suggester(Protocol):
    def ask(self, prompt: str) -> str: ...


class OpenRouterSuggester:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key, self.model = api_key, model

    def ask(self, prompt: str) -> str:
        answers: queue.Queue = queue.Queue()

        def work() -> None:
            try:
                answers.put(chat(self.api_key, self.model, prompt, reasoning=REASONING))
            except Exception as error:  # noqa: BLE001 - wird unten im aufrufenden Thread geworfen
                answers.put(error)

        # Als Daemon, damit eine hängende Anfrage den Server beim Beenden nicht aufhält
        threading.Thread(target=work, daemon=True).start()
        try:
            answer = answers.get(timeout=DEADLINE)
        except queue.Empty:
            raise TooSlow from None
        if isinstance(answer, Exception):
            raise answer
        return answer


class TooSlow(Exception):
    """Die KI hat die Gesamtfrist überschritten."""


def suggest(text: str, sectors: dict[str, str], suggester: Suggester) -> Suggestions:
    """Fragt die KI und behält nur Vorschläge mit überprüfbarem Zitat."""
    text = text[:MAX_TEXT]
    if not text.strip():
        return Suggestions(note="Die Website enthielt keinen auswertbaren Text.")
    options = "\n".join(f"{value}: {label}" for value, label in sectors.items())
    try:
        answer = suggester.ask(PROMPT.format(sectors=options, text=text))
    except TooSlow:
        return Suggestions(note="Die KI hat zu lange gebraucht, es gibt keine Vorschläge.")
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
