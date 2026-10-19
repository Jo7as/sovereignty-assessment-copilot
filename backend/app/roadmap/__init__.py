"""Roadmap aus einer Bewertung: Fragen an die Anbieter, Maßnahmen und drei Wellen.

- Jede Lücke wird zu einer Frage an den Anbieter. Für jede Frage wird gerechnet, wie weit
  eine günstige Antwort den Dienst allein heben könnte.
- Maßnahmen sind ein Wechsel der Variante beim selben Anbieter oder eine EU-Alternative aus
  der Datenbank. Aufgenommen wird nur, was die gesicherte oder mögliche Stufe verbessert.
- Priorität: Kritikalität mal Abstand zur Höchststufe.
- Wellen nach Aufwand: Klärungen und geringer Aufwand in Welle 1, mittlerer Aufwand in
  Welle 2, hoher Aufwand in Welle 3.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessment import AssessedService, InventoryAssessment
from app.models import (
    AiTraining,
    Criticality,
    DataExport,
    DataLocation,
    Jurisdiction,
    KeyManagement,
    MigrationEffort,
    Openness,
    OperationsLocation,
    RenewableEnergy,
    Service,
    TransferBasis,
)
from app.scoring import CRITICALITY_WEIGHT, MAX_LEVEL, CertificateFact, assess, assess_variant

# Ein Wechsel der Variante ist meist eine Vertragsänderung ohne Migration der Anwendung.
# Das ist eine Annahme, keine belegte Angabe.
VARIANT_SWITCH_EFFORT = MigrationEffort.MITTEL

# Klärungen mit Anbietern stehen immer in Welle 1, Maßnahmen je nach Aufwand
WAVE_BY_EFFORT = {MigrationEffort.GERING: 1, MigrationEffort.MITTEL: 2, MigrationEffort.HOCH: 3}
WAVE_TITLES = {
    1: "Schnelle Erfolge (0 bis 6 Monate)",
    2: "Mittelfristig (6 bis 18 Monate)",
    3: "Strategisch (ab 18 Monaten)",
}

# Frage an den Anbieter je fehlender Angabe, dazu der günstigste mögliche Wert
QUESTIONS = {
    "data_location": (
        "Wo werden unsere Daten gespeichert und verarbeitet, und ist ein Standort in der EU "
        "vertraglich zugesichert?",
        {"data_location": DataLocation.EU_ZUGESICHERT},
    ),
    "key_management": (
        "Können wir die Schlüssel für unsere Daten selbst verwalten, idealerweise außerhalb "
        "Ihrer Systeme?",
        {"key_management": KeyManagement.KUNDE_EXTERN},
    ),
    "transfer_basis": (
        "Auf welche Rechtsgrundlage stützen Sie Übermittlungen unserer Daten in Drittstaaten?",
        {"transfer_basis": TransferBasis.STANDARDVERTRAGSKLAUSELN},
    ),
    "governing_law": (
        "Welchem Recht unterliegt der Vertrag, und wo ist der Gerichtsstand?",
        {"governing_law": Jurisdiction.EU_EWR},
    ),
    "operations_location": (
        "Von wo aus werden Betrieb und Support geleistet, und hat Personal außerhalb der EU "
        "Zugriff?",
        {"operations_location": OperationsLocation.NUR_EU},
    ),
    "data_export": (
        "Können wir alle Daten jederzeit in offenen Formaten exportieren, auch bei Vertragsende?",
        {"data_export": DataExport.OFFENE_FORMATE},
    ),
    "openness": (
        "Beruht der Dienst auf offenen Standards oder offenem Quellcode?",
        {"openness": Openness.OPEN_SOURCE},
    ),
    "ai_training_on_customer_data": (
        "Werden unsere Daten zum Training von KI-Modellen genutzt, und lässt sich das "
        "ausschließen?",
        {"ai_training": AiTraining.NEIN},
    ),
    "renewable_energy": (
        "Wird der Dienst nachweislich mit erneuerbarer Energie betrieben?",
        {"renewable_energy": RenewableEnergy.NACHGEWIESEN},
    ),
    "certificates": (
        "Welche Zertifikate oder Testate liegen für diesen Dienst vor, etwa BSI C5 oder ISO 27001?",
        {"certificates": (CertificateFact("bsi-c5"),)},
    ),
    "dependencies": (
        "Welche Unterauftragnehmer und Zulieferer setzen Sie ein, und wo haben diese ihren Sitz?",
        {"dependencies_complete": True},
    ),
}


# Kurze Themenbezeichnung je Frage, für Überschriften in der Roadmap
TOPICS = {
    "data_location": "Datenstandort",
    "key_management": "Schlüsselverwaltung",
    "transfer_basis": "Übermittlungsgrundlage",
    "governing_law": "Vertragsrecht",
    "operations_location": "Ort von Betrieb und Support",
    "data_export": "Datenexport",
    "openness": "Offenheit",
    "ai_training_on_customer_data": "KI-Training",
    "renewable_energy": "Energieversorgung",
    "certificates": "Zertifikate",
    "dependencies": "Zulieferer",
}


class MeasureKind(StrEnum):
    VARIANTE = "VARIANTE"  # andere Variante beim selben Anbieter
    ALTERNATIVE = "ALTERNATIVE"  # Wechsel zu einer EU-Alternative


@dataclass(frozen=True)
class Question:
    provider: str
    service: str
    criticality: Criticality
    fact: str
    text: str
    level_now: int
    level_if_favourable: int  # wenn allein diese Frage günstig beantwortet wird
    # Kernfrage: Die Lücke begrenzt einen der schwächsten Zielbereiche und hält damit die
    # Gesamtstufe unten. Alle anderen Fragen verbessern nur Teilbereiche oder den Wert.
    is_core: bool


@dataclass(frozen=True)
class Measure:
    service: str
    criticality: Criticality
    kind: MeasureKind
    target: str
    effort: MigrationEffort
    wave: int
    level_before: int
    potential_before: int
    level_after: int
    potential_after: int
    score_before: float
    score_after: float
    note: str | None


@dataclass(frozen=True)
class WaveItem:
    title: str
    services: tuple[str, ...]
    criticality: Criticality
    effort: MigrationEffort | None
    level_now: int
    priority: int
    possible_gain: int  # um wie viele Stufen es bestenfalls besser werden kann


@dataclass(frozen=True)
class Roadmap:
    questions: tuple[Question, ...]
    measures: tuple[Measure, ...]
    waves: dict[int, tuple[WaveItem, ...]]


def build_roadmap(result: InventoryAssessment, session: Session, today: date) -> Roadmap:
    questions = [q for service in result.services for q in _questions(service, today)]
    # Wichtigste zuerst: hohe Kritikalität, dann größter möglicher Gewinn
    questions.sort(
        key=lambda q: (-CRITICALITY_WEIGHT[q.criticality], q.level_now - q.level_if_favourable)
    )
    measures = [m for service in result.services for m in _measures(service, session, today)]
    return Roadmap(tuple(questions), tuple(measures), _waves(result.services, questions, measures))


def priority(criticality: Criticality, level: int) -> int:
    return CRITICALITY_WEIGHT[criticality] * (MAX_LEVEL - level)


def _questions(service: AssessedService, today: date) -> list[Question]:
    assessment = service.assessment
    core_facts = {
        finding.fact
        for objective in assessment.weakest
        for finding in assessment.objectives[objective].limiting
        if finding.is_gap
    }
    found = []
    for fact in assessment.gaps:
        text, favourable = QUESTIONS[fact]
        improved = assess(replace(service.facts, **favourable), today)
        found.append(
            Question(
                provider=service.provider,
                service=service.name,
                criticality=service.criticality,
                fact=fact,
                text=text,
                level_now=service.assessment.level,
                level_if_favourable=improved.level,
                is_core=fact in core_facts,
            )
        )
    return found


def _measures(service: AssessedService, session: Session, today: date) -> list[Measure]:
    record = session.scalars(select(Service).where(Service.slug == service.slug)).one()
    before = service.assessment
    candidates = []
    for variant in record.variants:
        if variant.slug != service.variant_slug:
            candidates.append(
                (MeasureKind.VARIANTE, variant.name, VARIANT_SWITCH_EFFORT, None, variant)
            )
    for alternative in record.alternatives:
        default = next(v for v in alternative.alternative.variants if v.is_default)
        candidates.append(
            (
                MeasureKind.ALTERNATIVE,
                alternative.alternative.name,
                alternative.migration_effort,
                alternative.note,
                default,
            )
        )

    measures = []
    for kind, target, effort, note, variant in candidates:
        after = assess_variant(variant, today)
        if after.level <= before.level and after.potential <= before.potential:
            continue
        if after.level < before.level:
            warning = "Angaben zur Zielvariante fehlen, gesichert sinkt die Stufe bis zur Klärung."
            note = f"{note} {warning}" if note else warning
        measures.append(
            Measure(
                service=service.name,
                criticality=service.criticality,
                kind=kind,
                target=target,
                effort=effort,
                wave=WAVE_BY_EFFORT[effort],
                level_before=before.level,
                potential_before=before.potential,
                level_after=after.level,
                potential_after=after.potential,
                score_before=before.score,
                score_after=after.score,
                note=note,
            )
        )
    return measures


def _waves(
    services: tuple[AssessedService, ...], questions: list[Question], measures: list[Measure]
) -> dict[int, tuple[WaveItem, ...]]:
    level_of = {service.name: service.assessment.level for service in services}
    gain_of = {s.name: s.assessment.potential - s.assessment.level for s in services}
    items: dict[int, list[WaveItem]] = {1: [], 2: [], 3: []}

    by_provider: dict[str, list[Question]] = defaultdict(list)
    for question in questions:
        by_provider[question.provider].append(question)
    for provider, asked in by_provider.items():
        names = tuple(dict.fromkeys(q.service for q in asked))
        top = max(asked, key=lambda q: priority(q.criticality, q.level_now))
        core_topics = list(dict.fromkeys(TOPICS[q.fact] for q in asked if q.is_core))
        if len(core_topics) == 1:
            title = f"Kernfrage an {provider} klären: {core_topics[0]}"
        elif core_topics:
            title = f"{len(core_topics)} Kernfragen an {provider} klären: {', '.join(core_topics)}"
        else:
            title = f"{len(asked)} weitere Fragen an {provider} klären"
        items[1].append(
            WaveItem(
                title=title,
                services=names,
                criticality=top.criticality,
                effort=None,
                level_now=top.level_now,
                priority=priority(top.criticality, top.level_now),
                possible_gain=max(gain_of[name] for name in names),
            )
        )
    for measure in measures:
        verb = (
            "Variante wechseln zu" if measure.kind is MeasureKind.VARIANTE else "Wechsel prüfen zu"
        )
        items[measure.wave].append(
            WaveItem(
                title=f"{measure.service}: {verb} {measure.target}",
                services=(measure.service,),
                criticality=measure.criticality,
                effort=measure.effort,
                level_now=level_of[measure.service],
                priority=priority(measure.criticality, level_of[measure.service]),
                possible_gain=measure.potential_after - level_of[measure.service],
            )
        )

    def order(item: WaveItem) -> tuple:
        return (-item.priority, -item.possible_gain, item.title)

    return {wave: tuple(sorted(found, key=order)) for wave, found in items.items()}


__all__ = [
    "WAVE_BY_EFFORT",
    "WAVE_TITLES",
    "Measure",
    "MeasureKind",
    "Question",
    "Roadmap",
    "WaveItem",
    "build_roadmap",
]
