"""Lädt die Testverträge aus data/testdata/contracts/sources.yaml.

Die PDFs gehören den Herstellern und liegen deshalb nicht im Repository. Das Skript lädt sie
in data/testdata/contracts/pdf/ und prüft die Prüfsumme. Weicht sie ab, hat der Hersteller das
Dokument geändert, und die Musterlösung in gold/ muss neu geprüft werden.

Aufruf im Ordner backend/:  uv run python scripts/fetch_contracts.py
"""

import hashlib
import sys
from pathlib import Path

import httpx2
import yaml

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data" / "testdata" / "contracts"
PDF_DIR = CONTRACTS_DIR / "pdf"


def main() -> int:
    sources = yaml.safe_load((CONTRACTS_DIR / "sources.yaml").read_text())["contracts"]
    PDF_DIR.mkdir(exist_ok=True)
    problems = 0
    for source in sources:
        target = PDF_DIR / f"{source['id']}.pdf"
        if target.exists() and _sha256(target.read_bytes()) == source["sha256"]:
            print(f"vorhanden    {source['id']}")
            continue
        response = httpx2.get(source["url"], follow_redirects=True, timeout=60)
        response.raise_for_status()
        target.write_bytes(response.content)
        if _sha256(response.content) == source["sha256"]:
            print(f"geladen      {source['id']}")
        else:
            problems += 1
            print(f"ABWEICHUNG   {source['id']}: Der Hersteller hat das Dokument geändert.")
    return 1 if problems else 0


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
