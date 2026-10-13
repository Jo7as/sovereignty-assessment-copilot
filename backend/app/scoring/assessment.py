"""Bewertung einer Variante: Stufe je Zielbereich, Gesamtstufe und Souveränitätswert."""

from datetime import date

from app.scoring.model import (
    MAX_LEVEL,
    WEIGHTS,
    Finding,
    Objective,
    ObjectiveResult,
    ServiceAssessment,
    VariantFacts,
)
from app.scoring.rules import RULES


def assess(facts: VariantFacts, today: date) -> ServiceAssessment:
    objectives = {
        objective: _objective_result(rule(facts, today)) for objective, rule in RULES.items()
    }
    results = objectives.values()
    return ServiceAssessment(
        objectives=objectives,
        # Die Gesamtstufe ist der schwächste Zielbereich
        level=min(result.level for result in results),
        potential=min(result.potential for result in results),
        score=_score({objective: result.level for objective, result in objectives.items()}),
        potential_score=_score(
            {objective: result.potential for objective, result in objectives.items()}
        ),
        gaps=tuple(
            sorted(
                {
                    finding.fact
                    for result in results
                    for finding in result.findings
                    if finding.is_gap and finding.fact
                }
            )
        ),
    )


def _objective_result(findings: list[Finding]) -> ObjectiveResult:
    # Die Stufe eines Zielbereichs ist die niedrigste Obergrenze seiner Kriterien
    return ObjectiveResult(
        level=min(finding.ceiling for finding in findings),
        potential=min(finding.potential for finding in findings),
        findings=tuple(findings),
    )


def _score(levels: dict[Objective, int]) -> float:
    """Souveränitätswert nach Abschnitt 5 des Rahmenwerks: Anteil je Zielbereich mal Gewicht."""
    return sum(WEIGHTS[objective] * level / MAX_LEVEL for objective, level in levels.items())
