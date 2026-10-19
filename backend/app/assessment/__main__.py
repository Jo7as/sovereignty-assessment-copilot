"""Bewertet den IT-Bestand der Musterbank und gibt Heatmap und Gesamtwert aus.

Aufruf im Ordner backend/:
    uv run python -m app.assessment           nur Textvergleich, bei jedem Lauf gleich
    uv run python -m app.assessment --mit-ki  mit KI für offene Einträge
"""

import sys
from datetime import date

from sqlalchemy.orm import Session

from app.assessment import assess_inventory
from app.config import PROJECT_ROOT
from app.db import engine
from app.inventory import read_inventory
from app.matching.catalog import default_classifier
from app.scoring import Objective

SHORT = ("Stra", "Rech", "Date", "Oper", "Lief", "Tech", "Sich", "Umw")
CRITICALITY = {"HOCH": "hoch", "MITTEL": "mittel", "GERING": "gering"}


def cell(level: int, potential: int) -> str:
    return f"{level}" if level == potential else f"{level}({potential})"


def main(arguments: list[str]) -> int:
    path = PROJECT_ROOT / "data" / "testdata" / "musterbank-it-bestand.xlsx"
    inventory = read_inventory(path.read_bytes(), path.name)
    classifier = default_classifier() if "--mit-ki" in arguments else None
    with Session(engine) as session:
        result = assess_inventory(inventory.entries, session, date.today(), classifier)

        print(f"Musterbank AG: {len(inventory.entries)} Einträge, {len(result.services)} Dienste\n")
        print(f"{'Dienst':<34}{'Krit.':<8}" + "".join(f"{s:>6}" for s in SHORT) + f"{'Gesamt':>8}")
        for service in result.services:
            objectives = service.assessment.objectives
            cells = "".join(
                f"{cell(objectives[o].level, objectives[o].potential):>6}" for o in Objective
            )
            flag = " *" if service.needs_review else ""
            total = cell(service.assessment.level, service.assessment.potential)
            print(
                f"{service.name[:33]:<34}{CRITICALITY[service.criticality]:<8}{cells}{total:>8}{flag}"
            )

        portfolio = result.portfolio
        print("\nLesehilfe: 1(3) heißt gesichert 1, möglich 3. * heißt: Zuordnung noch ungeprüft.")
        print(
            f"\nGesamt, gewichtet nach Kritikalität: Stufe {portfolio.level:.1f} "
            f"(möglich {portfolio.potential:.1f}), Souveränitätswert {portfolio.score:.0f} "
            f"(möglich {portfolio.potential_score:.0f}) von 100"
        )
        print(
            f"Schwächster Dienst mit hoher Kritikalität: Stufe {portfolio.weakest_critical_level}, "
            f"betrifft {len(portfolio.weakest_critical_services)} Dienste"
        )
        print(
            "Verteilung der Gesamtstufen: "
            + ", ".join(
                f"Stufe {level}: {count}" for level, count in portfolio.distribution.items()
            )
        )
        print(
            f"Dienste mit fehlenden Angaben: {portfolio.provisional_services} "
            f"von {len(result.services)}"
        )

        if result.unmatched:
            print("\nNicht zugeordnet, zur Prüfung:")
            for entry in result.unmatched:
                print(f"  Zeile {entry.row}: {entry.service}")
        notes = [(s.name, note) for s in result.services for note in s.notes]
        if notes:
            print("\nHinweise:")
            for name, note in notes:
                print(f"  {name}: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
