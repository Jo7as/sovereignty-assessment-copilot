"""Namen für Rohfunde aus einer offenen Signaturliste (enthec/webappanalyzer, GPL-3.0).

Belegstufe „Signatur“: Die Liste sagt, welches Werkzeug hinter einer Skriptadresse steckt, aber
nicht, wem es gehört. Ein Treffer bekommt deshalb einen Namen, aber keinen Dienst, keinen
Rechtsraum und keine Stufe. Bewertet wird nur, was in der eigenen Datenbank steht.
Die Liste aktualisiert scripts/update_signatures.py.
"""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SIGNATURE_FILE = Path(__file__).resolve().parents[3] / "data" / "signatures" / "technologies.json"

# Die häufigsten Kategorien der Liste auf Deutsch, die übrigen bleiben im Original
CATEGORY_DE = {
    "Marketing automation": "Marketing-Automatisierung",
    "Ecommerce": "Onlinehandel",
    "Live chat": "Live-Chat",
    "Analytics": "Webanalyse",
    "CRM": "Kundenverwaltung (CRM)",
    "Personalisation": "Personalisierung",
    "Advertising": "Werbung",
    "Widgets": "Widgets",
    "Payment processors": "Zahlungsabwicklung",
    "Reviews": "Bewertungen",
    "Appointment scheduling": "Terminbuchung",
    "Page builders": "Website-Baukasten",
    "CMS": "Content-Management",
    "Security": "Sicherheit",
    "Customer data platform": "Kundendatenplattform",
    "A/B Testing": "A/B-Tests",
    "Cookie compliance": "Einwilligungsverwaltung",
    "Email": "E-Mail",
    "Recruitment & staffing": "Bewerbermanagement",
    "Search engines": "Suche",
    "Affiliate programs": "Partnerprogramme",
    "Video players": "Videoplayer",
    "Tag managers": "Tag-Manager",
    "Accessibility": "Barrierefreiheit",
    "Surveys": "Umfragen",
}


@dataclass(frozen=True)
class Tool:
    name: str
    website: str | None
    category: str | None


@dataclass(frozen=True)
class Signature:
    tool: Tool
    patterns: tuple[re.Pattern, ...]

    @classmethod
    def build(
        cls, name: str, patterns: list[str], website: str | None, categories: list[str]
    ) -> "Signature":
        compiled = []
        for pattern in patterns:
            # Zusätze wie „\;version:\1“ oder „\;confidence:50“ betreffen nur Wappalyzer selbst
            pattern = pattern.split("\\;")[0]
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                continue  # Javascript-Syntax, die Python nicht kennt: Muster auslassen
        category = CATEGORY_DE.get(categories[0], categories[0]) if categories else None
        return cls(Tool(name, website, category), tuple(compiled))

    def matches(self, url: str) -> bool:
        return any(pattern.search(url) for pattern in self.patterns)


@cache
def load_signatures() -> tuple[Signature, ...]:
    data = json.loads(SIGNATURE_FILE.read_text("utf-8"))
    return tuple(
        Signature.build(name, entry["scriptSrc"], entry.get("website"), entry.get("categories", []))
        for name, entry in data["technologies"].items()
    )


def identify(
    resources: Iterable[tuple[str, str]], signatures: tuple[Signature, ...]
) -> dict[str, Tool]:
    """Ordnet Hosts einem Werkzeug zu. Je Host gilt der erste Treffer."""
    tools: dict[str, Tool] = {}
    for host, path in sorted(resources):
        if host in tools:
            continue
        url = f"https://{host}{path}"
        if signature := next((s for s in signatures if s.matches(url)), None):
            tools[host] = signature.tool
    return tools
