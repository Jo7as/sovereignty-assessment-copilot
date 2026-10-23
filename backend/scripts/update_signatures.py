"""Lädt die Signaturliste von enthec/webappanalyzer und speichert eine Auswahl in data/signatures/.

Die Liste sagt, welches Werkzeug hinter einer Skriptadresse steckt, aber nicht, wem es gehört.
Behalten werden nur Dienste, die als SaaS markiert sind und an einer Skriptadresse erkennbar
sind. Selbst betriebene Technik wie jQuery ist für die Souveränität ohne Belang.

Die Daten stehen unter GPL-3.0 und bleiben deshalb in einer eigenen Datei, getrennt von den
eigenen Daten. Der Versionsstand ist fest, damit jede Aktualisierung bewusst geschieht.

Aufruf im Ordner backend/:  uv run python scripts/update_signatures.py [COMMIT]
"""

import json
import string
import sys
from datetime import date
from pathlib import Path

import httpx2

REPO = "enthec/webappanalyzer"
COMMIT = "d91f7e510e93457041bea874e8a9ffb011e3e4fe"  # Stand vom 19.10.2026
RAW = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
TARGET = Path(__file__).resolve().parents[2] / "data" / "signatures"


def fetch_json(commit: str, path: str) -> dict:
    response = httpx2.get(RAW.format(repo=REPO, commit=commit, path=path), timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"{path} ist kein JSON-Objekt")
    return data


def as_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def main() -> int:
    commit = sys.argv[1] if len(sys.argv) > 1 else COMMIT
    categories = fetch_json(commit, "src/categories.json")
    technologies: dict = {}
    for letter in ["_", *string.ascii_lowercase]:
        technologies |= fetch_json(commit, f"src/technologies/{letter}.json")

    selected = {}
    for name, entry in sorted(technologies.items()):
        patterns = as_list(entry.get("scriptSrc"))
        if not (isinstance(entry, dict) and entry.get("saas") is True and patterns):
            continue
        cats = [c for c in entry.get("cats", []) if str(c) in categories]
        selected[name] = {
            "scriptSrc": patterns,
            "website": entry.get("website") if isinstance(entry.get("website"), str) else None,
            "categories": [categories[str(c)]["name"] for c in cats],
        }

    TARGET.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": f"https://github.com/{REPO}/tree/{commit}",
        "license": "GPL-3.0",
        "retrieved": date.today().isoformat(),
        "technologies": selected,
    }
    (TARGET / "technologies.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    license_text = httpx2.get(RAW.format(repo=REPO, commit=commit, path="LICENSE"), timeout=30)
    license_text.raise_for_status()
    (TARGET / "LICENSE").write_text(license_text.text, encoding="utf-8")
    print(f"{len(selected)} von {len(technologies)} Technologien gespeichert (Stand {commit[:8]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
