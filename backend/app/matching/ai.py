"""Stufe 2 der Zuordnung: KI als Rückfall, austauschbar.

Die KI wählt ausschließlich aus dem Katalog oder antwortet „keiner“. Jede Antwort wird
geprüft, und ihre Vorschläge gelten als ungeprüft, bis ein Mensch sie bestätigt.
"""

import json
import re
from dataclasses import dataclass
from typing import Protocol

import httpx2

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


def chat(api_key: str, model: str, prompt: str, timeout: float = 60) -> str:
    """Eine Anfrage an ein Sprachmodell über OpenRouter, Antwort als Text."""
    response = httpx2.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0,
            # Nur Anbieter, die Anfragen weder speichern noch zum Training nutzen
            "provider": {"data_collection": "deny"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_answer(text: str) -> AiChoice:
    """Liest die JSON-Antwort. Die Antwort kommt von außen und wird nicht blind übernommen."""
    found = re.search(r"\{.*\}", text, re.DOTALL)
    if not found:
        return AiChoice(None, 0, "Die KI-Antwort war kein JSON.")
    try:
        data = json.loads(found.group(0))
    except json.JSONDecodeError:
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
