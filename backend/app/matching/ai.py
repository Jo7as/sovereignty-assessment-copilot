"""Anbindung der KI über OpenRouter, austauschbar.

Zuordnung (Stufe 2): Die KI wählt ausschließlich aus dem Katalog oder antwortet „keiner“.
Strukturierte Antworten (Stufe 3): Ein Pydantic-Modell beschreibt die Antwort. Daraus wird
das JSON-Schema für die Anfrage, und dasselbe Modell prüft die Antwort im Code.
Jede Antwort wird geprüft, und ihre Vorschläge gelten als ungeprüft, bis ein Mensch sie bestätigt.
"""

import json
import re
from dataclasses import dataclass
from typing import Protocol

import httpx2
from pydantic import BaseModel, ValidationError

from app.matching.text import CatalogService

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class AiChoice:
    slug: str | None
    confidence: float
    reason: str


class Classifier(Protocol):
    def choose(self, entry: dict[str, object], catalog: list[CatalogService]) -> AiChoice: ...


PROMPT = """Du ordnest Einträge aus dem IT-Bestand eines Unternehmens Diensten aus einem Katalog zu.

Eintrag:
{entry}

Katalog (slug | Name | Anbieter):
{catalog}

Regeln:
- Wähle genau einen slug aus dem Katalog oder null, wenn keiner passt.
- Eigenentwicklungen, interne Systeme und Dienste, die nicht im Katalog stehen, ergeben null.
- Rate nicht. Wenn du unsicher bist, setze die Konfidenz niedrig.

Antworte nur mit JSON:
{{"slug": "...", "confidence": 0.0 bis 1.0, "reason": "ein Satz auf Deutsch"}}"""


class OpenRouterClassifier:
    """Fragt ein Sprachmodell über OpenRouter. Das Modell ist frei wählbar."""

    def __init__(self, api_key: str, model: str, timeout: float = 60) -> None:
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def choose(self, entry: dict[str, object], catalog: list[CatalogService]) -> AiChoice:
        fields = ("service", "variant", "provider", "purpose")
        entry_text = "\n".join(f"- {key}: {entry[key]}" for key in fields if entry.get(key))
        catalog_text = "\n".join(f"{s.slug} | {s.name} | {s.provider}" for s in catalog)
        prompt = PROMPT.format(entry=entry_text, catalog=catalog_text)
        return parse_answer(chat(self.api_key, self.model, prompt, self.timeout))


def chat(
    api_key: str,
    model: str,
    prompt: str,
    timeout: float = 60,
    reasoning: dict | None = None,
    schema: dict | None = None,
) -> str:
    """Eine Anfrage an ein Sprachmodell über OpenRouter, Antwort als Text.

    `reasoning` steuert, wie lange das Modell vor der Antwort nachdenkt, etwa {"effort": "low"}.
    Ohne Angabe entscheidet das Modell selbst. `schema` ist ein JSON-Schema, an das sich die
    Antwort halten muss. Dann gehen Anfragen nur an Anbieter, die Schemas beherrschen.
    """
    body = {
        "model": model,
        "temperature": 0,
        # Nur Anbieter, die Anfragen weder speichern noch zum Training nutzen
        "provider": {"data_collection": "deny"},
        "messages": [{"role": "user", "content": prompt}],
    }
    if reasoning is not None:
        body["reasoning"] = reasoning
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "antwort", "strict": True, "schema": schema},
        }
        body["provider"]["require_parameters"] = True
    response = httpx2.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json=body,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


class InvalidAnswer(Exception):
    """Die Antwort der KI passt nicht zum verlangten Schema."""


RETRY = """

Deine letzte Antwort war ungültig: {error}
Antworte noch einmal, nur mit JSON nach dem verlangten Schema."""


def structured[T: BaseModel](
    api_key: str,
    model: str,
    prompt: str,
    answer: type[T],
    timeout: float = 60,
    reasoning: dict | None = None,
) -> T:
    """Fragt die KI mit Antwortschema und gibt die geprüfte Antwort zurück.

    Ist die Antwort ungültig, wird einmal mit dem Fehler nachgefragt, danach `InvalidAnswer`
    (docs/tiefenpruefung-ablauf.md, Abschnitt 7). Kann kein Anbieter ohne Datenspeicherung
    Schemas, wird ohne Schema gefragt. Geprüft wird die Antwort in jedem Fall im Code.
    """
    schema: dict | None = answer.model_json_schema()

    def ask(text: str) -> str:
        nonlocal schema
        try:
            return chat(api_key, model, text, timeout, reasoning, schema)
        except httpx2.HTTPStatusError as error:
            if schema is None or error.response.status_code != 404:
                raise
            schema = None  # OpenRouter: „No endpoints found“ für diese Parameter
            return chat(api_key, model, text, timeout, reasoning)

    try:
        return parse_structured(ask(prompt), answer)
    except InvalidAnswer as error:
        return parse_structured(ask(prompt + RETRY.format(error=error)), answer)


def parse_structured[T: BaseModel](text: str, answer: type[T]) -> T:
    data = json_object(text)
    if data is None:
        raise InvalidAnswer("Die Antwort enthielt kein JSON-Objekt.")
    try:
        return answer.model_validate(data)
    except ValidationError as error:
        problems = [
            f"{'.'.join(str(part) for part in item['loc']) or 'Antwort'}: {item['msg']}"
            for item in error.errors()[:5]
        ]
        raise InvalidAnswer("; ".join(problems)) from None


def json_object(text: str) -> dict | None:
    """Das JSON-Objekt in einer Antwort, auch mit Text drumherum. Sonst None."""
    found = re.search(r"\{.*\}", text, re.DOTALL)
    if not found:
        return None
    try:
        data = json.loads(found.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_answer(text: str) -> AiChoice:
    """Liest die JSON-Antwort. Die Antwort kommt von außen und wird nicht blind übernommen."""
    data = json_object(text)
    if data is None:
        return AiChoice(None, 0, "Die KI-Antwort war kein gültiges JSON.")
    slug = data.get("slug")
    try:
        confidence = min(max(float(data.get("confidence", 0)), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return AiChoice(
        slug if isinstance(slug, str) and slug else None,
        confidence,
        str(data.get("reason", ""))[:500],
    )
