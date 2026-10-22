"""Prüft die Nachweise der Anbieterdaten nach.

Ruft jede Quelle aus data/ ab und kontrolliert, ob die Fundstelle dort wörtlich steht.
Das findet erfundene und veraltete Fundstellen. Ob eine Fundstelle richtig ausgelegt
wurde, prüft das Skript nicht.

Manche Seiten sperren automatische Abrufe. Hat ein Mensch die Fundstelle dort im Browser
geprüft, steht das im Feld verified_by. Solche Angaben ruft das Skript nicht ab, sondern
zählt sie gesondert.

Aufruf im Ordner backend/:  uv run python scripts/verify_evidence.py
"""

import html
import io
import logging
import re
import sys
from collections.abc import Iterator
from pathlib import Path

import httpx2
import yaml
from pypdf import PdfReader

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
# pypdf meldet fehlende Schriftdetails, die für die Textsuche keine Rolle spielen
logging.getLogger("pypdf").setLevel(logging.ERROR)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en,de;q=0.8",
}
TYPOGRAPHY = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-"})


def comparable(text: str) -> str:
    """Entfernt Leerraum und typografische Unterschiede, damit nur der Wortlaut zählt."""
    return re.sub(r"\s+", "", text.replace(" ", " ").translate(TYPOGRAPHY))


def page_text(url: str) -> str:
    response = httpx2.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    response.raise_for_status()
    if response.content.startswith(b"%PDF"):
        pages = PdfReader(io.BytesIO(response.content)).pages
        return " ".join(page.extract_text() or "" for page in pages)
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", response.text)
    return html.unescape(re.sub(r"(?s)<[^>]+>", " ", text))


def find_evidence(node: object, path: str) -> Iterator[tuple[str, dict]]:
    """Liefert jede Angabe mit Quelle samt ihrem Pfad in der Datei."""
    if isinstance(node, dict):
        if "source" in node:
            yield path, node
        for key, value in node.items():
            yield from find_evidence(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            if isinstance(item, dict):
                label = item.get("slug") or item.get("certificate") or item.get("supplier") or index
                yield from find_evidence(item, f"{path}[{label}]")


def main() -> int:
    pages: dict[str, str | Exception] = {}
    confirmed = 0
    by_human: list[str] = []
    problems: list[str] = []

    for file in sorted(DATA_DIR.rglob("*.yaml")):
        if file.name.startswith("_"):
            continue
        content = yaml.safe_load(file.read_text(encoding="utf-8"))
        for path, evidence in find_evidence(content, ""):
            where = f"{file.relative_to(DATA_DIR)}: {path}"
            url, quote = evidence["source"], evidence.get("quote")
            if not quote:
                problems.append(f"OHNE FUNDSTELLE  {where}")
                continue
            if evidence.get("verified_by"):
                by_human.append(f"{where}  ({evidence['verified_by']})")
                continue
            if url not in pages:
                try:
                    pages[url] = comparable(page_text(url))
                except Exception as error:  # noqa: BLE001 - jede Abruf-Störung wird gemeldet
                    pages[url] = error
            page = pages[url]
            if isinstance(page, Exception):
                problems.append(
                    f"NICHT ABRUFBAR   {where}\n                 {url}\n                 {page}"
                )
            elif comparable(quote) not in page:
                problems.append(f"NICHT GEFUNDEN   {where}\n                 {url}")
            else:
                confirmed += 1

    print(
        f"{confirmed} Fundstellen bestätigt, {len(by_human)} von einem Menschen bestätigt, "
        f"{len(problems)} Probleme, {len(pages)} Quellen geladen"
    )
    for entry in by_human:
        print(f"VON HAND GEPRÜFT {entry}")
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
