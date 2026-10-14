"""Begriffe der Bewertung: Zielbereiche, Fakten eines Dienstes und Ergebnisse."""

from dataclasses import dataclass
from datetime import date
from enum import auto

from app.models.enums import (
    AiTraining,
    DataExport,
    DataLocation,
    DependencyKind,
    Jurisdiction,
    KeyManagement,
    Openness,
    OperationsLocation,
    RenewableEnergy,
    TransferBasis,
    Values,
)

MAX_LEVEL = 4


class Objective(Values):
    """Die acht Zielbereiche des EU Cloud Sovereignty Framework (SOV-1 bis SOV-8)."""

    STRATEGISCH = auto()
    RECHTLICH = auto()
    DATEN_KI = auto()
    OPERATIV = auto()
    LIEFERKETTE = auto()
    TECHNOLOGIE = auto()
    SICHERHEIT = auto()
    UMWELT = auto()


# Zielbereiche, aus denen die Gesamtstufe entsteht. Umwelt zählt nur im Souveränitätswert:
# Die Stufen beschreiben Kontrolle durch Nicht-EU-Akteure, dazu sagt die Energieversorgung
# nichts. Entscheidung von Jonas vom 14.10.2026, siehe docs/bewertungslogik.md.
OVERALL_OBJECTIVES = tuple(
    objective for objective in Objective if objective is not Objective.UMWELT
)

# Gewichte in Prozent für den Souveränitätswert, Abschnitt 5 des Rahmenwerks
WEIGHTS = {
    Objective.STRATEGISCH: 15,
    Objective.RECHTLICH: 10,
    Objective.DATEN_KI: 10,
    Objective.OPERATIV: 15,
    Objective.LIEFERKETTE: 20,
    Objective.TECHNOLOGIE: 15,
    Objective.SICHERHEIT: 10,
    Objective.UMWELT: 5,
}


# Schutz vor dem Zugriff fremder Behörden, vom schwächsten zum stärksten Rechtsraum
_PROTECTION = {
    Jurisdiction.DRITTSTAAT: 0,
    Jurisdiction.USA: 0,
    Jurisdiction.ANGEMESSEN: 1,
    Jurisdiction.EU_EWR: 2,
}


def weakest(*jurisdictions: Jurisdiction) -> Jurisdiction:
    """Der Rechtsraum mit dem geringsten Schutz vor dem Zugriff fremder Behörden."""
    return min(jurisdictions, key=_PROTECTION.__getitem__)


@dataclass(frozen=True)
class CertificateFact:
    slug: str
    valid_until: date | None = None


@dataclass(frozen=True)
class DependencyFact:
    supplier: str
    jurisdiction: Jurisdiction  # Rechtsraum der Konzernmutter des Zulieferers
    kind: DependencyKind
    critical: bool


@dataclass(frozen=True)
class VariantFacts:
    """Alles, was die Regeln über eine Variante wissen müssen. Keine Datenbank nötig."""

    # Rechtsraum der Konzernmutter des Anbieters: Von dort stammt die Technologie
    provider_jurisdiction: Jurisdiction
    # Rechtsraum der Konzernmutter des Betreibers, falls ein anderer den Dienst betreibt
    operator_jurisdiction: Jurisdiction | None
    # Sitz der Betreibergesellschaft selbst
    operator_seat: Jurisdiction | None
    data_location: DataLocation
    operations_location: OperationsLocation
    transfer_basis: TransferBasis
    governing_law: Jurisdiction | None
    key_management: KeyManagement
    data_export: DataExport
    openness: Openness
    ai_training: AiTraining
    renewable_energy: RenewableEnergy
    certificates: tuple[CertificateFact, ...]
    dependencies: tuple[DependencyFact, ...]
    # Ist die Liste der Zulieferer vollständig geprüft?
    dependencies_complete: bool

    @property
    def controller_jurisdiction(self) -> Jurisdiction:
        """Rechtsraum dessen, der über den Dienst entscheidet.

        Betreibt eine eigene Gesellschaft den Dienst, zählt der schwächere Rechtsraum aus
        ihrem Sitz und dem ihrer Konzernmutter: Beide können zur Herausgabe verpflichtet werden.
        """
        if self.operator_jurisdiction is None or self.operator_seat is None:
            return self.provider_jurisdiction
        return weakest(self.operator_jurisdiction, self.operator_seat)

    @property
    def has_eu_operating_company(self) -> bool:
        return self.operator_seat is Jurisdiction.EU_EWR


@dataclass(frozen=True)
class Finding:
    """Ein Kriterium eines Zielbereichs und die Stufe, die es höchstens zulässt."""

    criterion: str
    ceiling: int  # gesichert: Unbekanntes zählt wie der ungünstigste Fall
    potential: int  # möglich: Unbekanntes zählt wie der günstigste Fall
    reason: str
    fact: str | None = None  # Name des Merkmals, unter dem der Nachweis abgelegt ist

    @property
    def is_gap(self) -> bool:
        return self.potential > self.ceiling


@dataclass(frozen=True)
class ObjectiveResult:
    level: int
    potential: int
    findings: tuple[Finding, ...]

    @property
    def limiting(self) -> tuple[Finding, ...]:
        """Die Kriterien, an denen eine höhere Stufe scheitert."""
        if self.level == MAX_LEVEL:
            return ()
        return tuple(finding for finding in self.findings if finding.ceiling == self.level)


@dataclass(frozen=True)
class ServiceAssessment:
    objectives: dict[Objective, ObjectiveResult]
    level: int
    potential: int
    score: float  # Souveränitätswert 0 bis 100
    potential_score: float
    gaps: tuple[str, ...]  # Merkmale, deren Klärung die Stufe heben könnte

    @property
    def is_provisional(self) -> bool:
        return bool(self.gaps)

    @property
    def weakest(self) -> tuple[Objective, ...]:
        return tuple(o for o in OVERALL_OBJECTIVES if self.objectives[o].level == self.level)
