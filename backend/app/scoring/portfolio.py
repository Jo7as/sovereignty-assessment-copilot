"""Gesamtwert für ein Unternehmen: alle Dienste, gewichtet nach Kritikalität."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.models.enums import Criticality
from app.scoring.model import MAX_LEVEL, Objective, ServiceAssessment

# Ein Dienst mit hoher Kritikalität zählt dreimal so viel wie einer mit geringer
CRITICALITY_WEIGHT = {Criticality.GERING: 1, Criticality.MITTEL: 2, Criticality.HOCH: 3}


@dataclass(frozen=True)
class PortfolioItem:
    name: str
    criticality: Criticality
    assessment: ServiceAssessment


@dataclass(frozen=True)
class PortfolioAssessment:
    # Gewichtete Mittelwerte, gesichert und möglich
    level: float
    potential: float
    levels: dict[Objective, float]
    potentials: dict[Objective, float]
    score: float
    potential_score: float
    # Der schwächste Dienst mit hoher Kritikalität: Ein Mittelwert darf ihn nicht verdecken
    weakest_critical_level: int | None
    weakest_critical_services: tuple[str, ...]
    distribution: dict[int, int]  # Anzahl der Dienste je Gesamtstufe
    provisional_services: int  # Dienste, bei denen Angaben fehlen


def assess_portfolio(items: Sequence[PortfolioItem]) -> PortfolioAssessment:
    if not items:
        raise ValueError("Ein Portfolio braucht mindestens einen Dienst.")

    total_weight = sum(CRITICALITY_WEIGHT[item.criticality] for item in items)

    def weighted_mean(value: Callable[[ServiceAssessment], float]) -> float:
        return sum(
            CRITICALITY_WEIGHT[item.criticality] * value(item.assessment) for item in items
        ) / (total_weight)

    critical = [item for item in items if item.criticality is Criticality.HOCH]
    weakest = min((item.assessment.level for item in critical), default=None)

    return PortfolioAssessment(
        level=weighted_mean(lambda assessment: assessment.level),
        potential=weighted_mean(lambda assessment: assessment.potential),
        levels={
            objective: weighted_mean(lambda assessment, o=objective: assessment.objectives[o].level)
            for objective in Objective
        },
        potentials={
            objective: weighted_mean(
                lambda assessment, o=objective: assessment.objectives[o].potential
            )
            for objective in Objective
        },
        score=weighted_mean(lambda assessment: assessment.score),
        potential_score=weighted_mean(lambda assessment: assessment.potential_score),
        weakest_critical_level=weakest,
        weakest_critical_services=tuple(
            item.name for item in critical if item.assessment.level == weakest
        ),
        distribution={
            level: sum(item.assessment.level == level for item in items)
            for level in range(MAX_LEVEL + 1)
        },
        provisional_services=sum(item.assessment.is_provisional for item in items),
    )
