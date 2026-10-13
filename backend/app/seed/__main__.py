"""Aufruf im Ordner backend/:  uv run python -m app.seed"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.db import engine
from app.seed import SeedError, load_seed


def main(data_dir: Path = PROJECT_ROOT / "data") -> int:
    with Session(engine) as session:
        try:
            report = load_seed(session, data_dir)
        except SeedError as error:
            print(f"{len(error.errors)} Fehler in den Seed-Dateien, nichts wurde geschrieben:")
            for message in error.errors:
                print(f"  {message}")
            return 1
        session.commit()

    print(
        f"Geladen: {report.services} Dienste mit {report.variants} Varianten, "
        f"{report.organizations} Unternehmen, {report.countries} Länder, "
        f"{report.categories} Kategorien, {report.certificates} Zertifikate, "
        f"{report.evidence} Nachweise"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
