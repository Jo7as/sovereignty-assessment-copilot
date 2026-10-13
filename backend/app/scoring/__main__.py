"""Bewertet alle Varianten der Anbieterdatenbank und gibt die Heatmap als Text aus.

Aufruf im Ordner backend/:  uv run python -m app.scoring
Mit Begründung für einen Dienst:  uv run python -m app.scoring personio
"""

import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import Service, ServiceVariant
from app.scoring import (
    Objective,
    PortfolioItem,
    ServiceAssessment,
    assess_portfolio,
    assess_variant,
)

SHORT = {
    Objective.STRATEGISCH: "Stra",
    Objective.RECHTLICH: "Rech",
    Objective.DATEN_KI: "Date",
    Objective.OPERATIV: "Oper",
    Objective.LIEFERKETTE: "Lief",
    Objective.TECHNOLOGIE: "Tech",
    Objective.SICHERHEIT: "Sich",
    Objective.UMWELT: "Umw",
}


def cell(level: int, potential: int) -> str:
    """Gesicherte Stufe, in Klammern die mögliche, falls Angaben fehlen."""
    return f"{level}" if level == potential else f"{level}({potential})"


def print_heatmap(rows: list[tuple[ServiceVariant, ServiceAssessment]]) -> None:
    header = f"{'Dienst':<44}" + "".join(f"{SHORT[o]:>6}" for o in Objective)
    print(header + f"{'Gesamt':>8}{'Wert':>12}")
    for variant, result in rows:
        name = f"{variant.service.name} / {variant.name}"[:43]
        cells = "".join(f"{cell(r.level, r.potential):>6}" for r in result.objectives.values())
        score = f"{result.score:.0f}" + (
            f" ({result.potential_score:.0f})" if result.is_provisional else ""
        )
        print(f"{name:<44}{cells}{cell(result.level, result.potential):>8}{score:>12}")
    print("\nLesehilfe: 1(3) bedeutet gesichert Stufe 1, möglich Stufe 3, weil Angaben fehlen.")


def print_reasons(variant: ServiceVariant, result: ServiceAssessment) -> None:
    print(f"\n{variant.service.name} / {variant.name}")
    for objective, objective_result in result.objectives.items():
        print(f"  {objective}: {cell(objective_result.level, objective_result.potential)}")
        for finding in objective_result.findings:
            marker = "?" if finding.is_gap else " "
            print(
                f"    {marker} höchstens {finding.ceiling}  {finding.criterion}: {finding.reason}"
            )


def main(arguments: list[str]) -> int:
    today = date.today()
    with Session(engine) as session:
        variants = session.scalars(
            select(ServiceVariant).join(Service).order_by(Service.name, ServiceVariant.id)
        ).all()
        rows = [(variant, assess_variant(variant, today)) for variant in variants]
        if not rows:
            print("Die Datenbank enthält keine Dienste. Zuerst: uv run python -m app.seed")
            return 1

        if arguments:
            selected = [row for row in rows if row[0].service.slug == arguments[0]]
            if not selected:
                print(f"Kein Dienst mit dem slug „{arguments[0]}“ gefunden.")
                return 1
            for variant, result in selected:
                print_reasons(variant, result)
            return 0

        print_heatmap(rows)
        portfolio = assess_portfolio(
            [
                PortfolioItem(variant.service.name, variant.service.typical_criticality, result)
                for variant, result in rows
                if variant.is_default
            ]
        )
        print(
            f"\nAlle Dienste als ein Portfolio (Standardvarianten, übliche Kritikalität): "
            f"Stufe {portfolio.level:.1f} (möglich {portfolio.potential:.1f}), "
            f"Wert {portfolio.score:.0f} (möglich {portfolio.potential_score:.0f}) von 100"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
