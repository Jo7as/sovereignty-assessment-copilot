"""Erzeugt die Excel-Vorlage für den IT-Bestand, auf Wunsch mit den Testdaten der Musterbank.

Aufruf im Ordner backend/:
    uv run python -m app.inventory               leere Vorlage
    uv run python -m app.inventory --musterbank  IT-Bestand der Musterbank AG
"""

import sys

import yaml

from app.config import PROJECT_ROOT
from app.inventory import build_template

DATA_DIR = PROJECT_ROOT / "data"


def main(arguments: list[str]) -> int:
    if "--musterbank" in arguments:
        rows = yaml.safe_load(
            (DATA_DIR / "testdata" / "musterbank.yaml").read_text(encoding="utf-8")
        )
        path = build_template(DATA_DIR / "testdata" / "musterbank-it-bestand.xlsx", rows)
        print(f"{len(rows)} Einträge geschrieben: {path.relative_to(PROJECT_ROOT)}")
    else:
        path = build_template(DATA_DIR / "templates" / "it-bestand-vorlage.xlsx")
        print(f"Vorlage geschrieben: {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
