"""Erzeugt die Excel-Vorlage für den IT-Bestand.

Aufruf im Ordner backend/:  uv run python -m app.inventory
"""

from app.config import PROJECT_ROOT
from app.inventory import build_template

if __name__ == "__main__":
    path = build_template(PROJECT_ROOT / "data" / "templates" / "it-bestand-vorlage.xlsx")
    print(f"Vorlage geschrieben: {path.relative_to(PROJECT_ROOT)}")
