"""Prüft die Nachweise der Anbieterdaten nach.

Ruft jede Quelle aus data/ ab und kontrolliert, ob die Fundstelle dort wörtlich steht.
Das findet erfundene und veraltete Fundstellen. Ob eine Fundstelle richtig ausgelegt
wurde, prüft das Skript nicht.

Reihenfolge je Fundstelle: zuerst die Quelle selbst, dann die jüngste Kopie im Internet
Archive (Wayback Machine), zuletzt der Vermerk verified_by, wenn ein Mensch die Fundstelle im
Browser geprüft hat. Bot-Sperren werden nicht umgangen, das Archiv ist eine eigene, öffentliche
Quelle mit Datum.

Aufruf im Ordner backend/:  uv run python scripts/verify_evidence.py
"""

import html
import io
import logging
import re
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
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
ARCHIVE_API = "https://archive.org/wayback/available"
ARCHIVE_PAUSE = 5  # Sekunden zwischen Abrufen beim Archiv, sonst antwortet es mit 429
ARCHIVE_RETRIES = 3
TYPOGRAPHY = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-"})


def comparable(text: str) -> str:
    """Entfernt Leerraum und typografische Unterschiede, damit nur der Wortlaut zählt."""
    return re.sub(r"\s+", "", text.replace(" ", " ").translate(TYPOGRAPHY))


def page_text(url: str) -> str:
    response = httpx2.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return _text(response)


def _text(response: httpx2.Response) -> str:
    if response.content.startswith(b"%PDF"):
        pages = PdfReader(io.BytesIO(response.content)).pages
        return " ".join(page.extract_text() or "" for page in pages)
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", response.text)
    return html.unescape(re.sub(r"(?s)<[^>]+>", " ", text))


@dataclass(frozen=True)
class Snapshot:
    url: str
    date: str  # JJJJ-MM-TT
    text: str


def _archive_get(address: str, params: dict | None = None) -> httpx2.Response:
    """Abruf beim Archiv mit Pause. Bittet es um Geduld (429), wartet das Skript so lange, wie
    das Archiv im Kopf Retry-After verlangt, sonst immer länger, höchstens zwei Minuten."""
    time.sleep(ARCHIVE_PAUSE)
    for attempt in range(ARCHIVE_RETRIES):
        response = httpx2.get(
            address, params=params, headers=HEADERS, timeout=60, follow_redirects=True
        )
        if response.status_code != 429:
            break
        wait = response.headers.get("Retry-After", "")
        time.sleep(min(int(wait) if wait.isdigit() else 30 * (attempt + 1), 120))
    response.raise_for_status()
    return response


def archived(url: str) -> Snapshot | None:
    """Jüngste Kopie der Seite im Internet Archive, als unveränderter Originalinhalt."""
    closest = (
        _archive_get(ARCHIVE_API, {"url": url}).json().get("archived_snapshots", {}).get("closest")
    )
    if not closest or not closest.get("available"):
        return None
    stamp = closest["timestamp"]
    # „id_“ liefert die Seite, wie sie war, ohne die Leiste des Archivs
    raw = f"https://web.archive.org/web/{stamp}id_/{url}"
    return Snapshot(raw, f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}", _text(_archive_get(raw)))


def _first_line(error: Exception) -> str:
    return str(error).splitlines()[0] if str(error) else type(error).__name__


@dataclass(frozen=True)
class Result:
    kind: str  # DIREKT, ARCHIV, MENSCH oder PROBLEM
    detail: str = ""


class Checker:
    """Prüft Fundstellen und lädt jede Quelle und jede Archivkopie nur einmal."""

    def __init__(
        self,
        load_page: Callable[[str], str] = page_text,
        load_archive: Callable[[str], Snapshot | None] = archived,
    ) -> None:
        self.load_page, self.load_archive = load_page, load_archive
        self.pages: dict[str, str | Exception] = {}
        self.snapshots: dict[str, Snapshot | None | Exception] = {}

    def check(self, evidence: dict) -> Result:
        url, quote = evidence["source"], evidence.get("quote")
        if not quote:
            return Result("PROBLEM", "ohne Fundstelle")
        wanted = comparable(quote)
        if url not in self.pages:
            try:
                self.pages[url] = comparable(self.load_page(url))
            except Exception as error:  # noqa: BLE001 - jede Abruf-Störung wird gemeldet
                self.pages[url] = error
        page = self.pages[url]
        if isinstance(page, str) and wanted in page:
            return Result("DIREKT")
        if url not in self.snapshots:
            try:
                self.snapshots[url] = self.load_archive(url)
            except Exception as error:  # noqa: BLE001 - Archiv gestört: weiter zum Menschen
                self.snapshots[url] = error
        snapshot = self.snapshots[url]
        if isinstance(snapshot, Snapshot) and wanted in comparable(snapshot.text):
            return Result("ARCHIV", f"Archivkopie vom {snapshot.date}: {snapshot.url}")
        if isinstance(snapshot, Exception):
            archive = f"Archiv nicht erreichbar ({_first_line(snapshot)})"
        elif snapshot is None:
            archive = "keine Archivkopie"
        else:
            archive = f"Archivkopie vom {snapshot.date} ohne die Fundstelle"
        if evidence.get("verified_by"):
            return Result("MENSCH", f"{evidence['verified_by']}; {archive}")
        reason = (
            f"nicht abrufbar ({_first_line(page)})"
            if isinstance(page, Exception)
            else "nicht gefunden"
        )
        return Result("PROBLEM", f"{reason}; {archive}")


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
    checker = Checker()
    found: dict[str, list[str]] = {"DIREKT": [], "ARCHIV": [], "MENSCH": [], "PROBLEM": []}

    for file in sorted(DATA_DIR.rglob("*.yaml")):
        if file.name.startswith("_"):
            continue
        content = yaml.safe_load(file.read_text(encoding="utf-8"))
        for path, evidence in find_evidence(content, ""):
            result = checker.check(evidence)
            where = f"{file.relative_to(DATA_DIR)}: {path}"
            found[result.kind].append(
                f"{where}\n                 {evidence['source']}\n                 {result.detail}"
            )

    print(
        f"{len(found['DIREKT'])} Fundstellen direkt bestätigt, "
        f"{len(found['ARCHIV'])} über das Internet Archive, "
        f"{len(found['MENSCH'])} nur von einem Menschen, {len(found['PROBLEM'])} Probleme"
    )
    for kind, label in (
        ("ARCHIV", "ARCHIVKOPIE     "),
        ("MENSCH", "VON HAND GEPRÜFT"),
        ("PROBLEM", "PROBLEM         "),
    ):
        for entry in found[kind]:
            print(f"{label} {entry}")
    return 1 if found["PROBLEM"] else 0


if __name__ == "__main__":
    sys.exit(main())
