"""Welches Recht gilt, und welche Pflichten sind offen? DORA und NIS2 aus Fragebogen und Bestand.

Die Fundstellen stehen in data/compliance.yaml und data/questionnaire.yaml. Erläutert in
docs/bewertungslogik.md, Abschnitt „DORA und NIS2“.

Fehlt eine Angabe, die über die Anwendbarkeit entscheidet, lautet das Ergebnis „nicht
bestimmbar“. Geraten wird nicht.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, fields
from decimal import Decimal
from enum import auto
from functools import cache

import yaml
from pydantic import BaseModel, ConfigDict

from app.assessment import AssessedService
from app.config import PROJECT_ROOT
from app.models.enums import Values
from app.questionnaire import Basis, Questionnaire
from app.questionnaire.answers import AnswerValue

COMPLIANCE_FILE = PROJECT_ROOT / "data" / "compliance.yaml"
# Stufe, ab der eine Antwort als erfüllt gilt: schriftlich festgelegt oder besser
FULFILLED_LEVEL = 3
HARD_TO_REPLACE = ("nicht ersetzbar", "sehr komplex")


class Status(Values):
    GILT = auto()
    GILT_NICHT = auto()
    NICHT_BESTIMMBAR = auto()


class EntityClass(Values):
    WESENTLICH = auto()
    WICHTIG = auto()


class Severity(Values):
    LUECKE = auto()  # Stufe 0: nicht erfüllt
    TEILWEISE = auto()  # Stufe 1 oder 2: begonnen, aber nicht festgelegt


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InventoryHintRule(Model):
    code: str
    title: str
    explanation: str
    basis: tuple[Basis, ...]


class ComplianceRules(Model):
    citations: dict[str, Basis]
    inventory_hints: tuple[InventoryHintRule, ...]

    def hint(self, code: str) -> InventoryHintRule:
        return next(rule for rule in self.inventory_hints if rule.code == code)


@cache
def load_rules() -> ComplianceRules:
    return ComplianceRules.model_validate(
        yaml.safe_load(COMPLIANCE_FILE.read_text(encoding="utf-8"))
    )


@dataclass(frozen=True)
class Regime:
    law: str
    status: Status
    reasons: tuple[str, ...]
    basis: tuple[Basis, ...]
    entity_class: EntityClass | None = None  # nur NIS2
    microenterprise: bool | None = None  # nur DORA, Kleinstunternehmen haben Erleichterungen


@dataclass(frozen=True)
class Regulation:
    dora: Regime
    nis2: Regime
    # DORA geht der NIS2 für Finanzunternehmen vor (Art. 1 Abs. 2 DORA, Art. 4 NIS2)
    dora_precedes_nis2: bool

    @property
    def applicable_laws(self) -> frozenset[str]:
        laws = set()
        if self.dora.status is Status.GILT:
            laws.add("DORA")
        if self.nis2.status is Status.GILT and not self.dora_precedes_nis2:
            laws.add("NIS2")
        return frozenset(laws)


@dataclass(frozen=True)
class QuestionHint:
    question: str
    text: str
    answer: str
    severity: Severity
    basis: tuple[Basis, ...]


@dataclass(frozen=True)
class InventoryHint:
    code: str
    title: str
    explanation: str
    services: tuple[str, ...]
    basis: tuple[Basis, ...]
    group: str | None = None  # nur beim Konzentrationsrisiko


# ---------------------------------------------------------------- Welches Recht gilt


def determine_regulation(
    questionnaire: Questionnaire, answers: dict[str, AnswerValue]
) -> Regulation:
    rules = load_rules()
    cite = rules.citations
    sector_value = answers.get("sector")
    sector = next(
        (o for o in questionnaire.question("sector").options if o.value == sector_value), None
    )
    if sector is None:
        missing = ("Der Sektor ist nicht angegeben.",)
        return Regulation(
            Regime("DORA", Status.NICHT_BESTIMMBAR, missing, (cite["dora_scope"],)),
            Regime("NIS2", Status.NICHT_BESTIMMBAR, missing, (cite["nis2_scope"],)),
            dora_precedes_nis2=False,
        )

    size = _Size(
        employees=_number(answers.get("employees")),
        turnover=_number(answers.get("annual_turnover")),
        balance=_number(answers.get("balance_sheet_total")),
    )
    dora = _dora(sector.dora, sector.label, size, cite)
    nis2 = _nis2(sector.nis2_annex, sector.label, size, cite)
    precedes = dora.status is Status.GILT and nis2.status is Status.GILT
    if precedes:
        nis2 = Regime(
            nis2.law,
            nis2.status,
            (
                *nis2.reasons,
                "Für Finanzunternehmen gilt DORA als sektorspezifischer Rechtsakt. Die "
                "Pflichten zum Risikomanagement und zur Meldung von Vorfällen richten sich "
                "deshalb nach DORA.",
            ),
            (*nis2.basis, cite["dora_precedes_nis2"], cite["nis2_sector_acts"]),
            nis2.entity_class,
        )
    return Regulation(dora, nis2, dora_precedes_nis2=precedes)


def _dora(financial: bool, label: str, size: "_Size", cite: dict[str, Basis]) -> Regime:
    if not financial:
        return Regime(
            "DORA",
            Status.GILT_NICHT,
            (f"„{label}“ ist kein Finanzunternehmen im Sinne von Art. 2 DORA.",),
            (cite["dora_scope"],),
        )
    micro = size.is_dora_microenterprise()
    reasons = [f"„{label}“ ist ein Finanzunternehmen im Sinne von Art. 2 DORA."]
    basis = [cite["dora_scope"]]
    if micro is True:
        reasons.append("Als Kleinstunternehmen gelten Erleichterungen, etwa bei der Strategie.")
        basis.append(cite["dora_microenterprise"])
    elif micro is None:
        reasons.append("Ob Erleichterungen für Kleinstunternehmen greifen, ist offen.")
    return Regime("DORA", Status.GILT, tuple(reasons), tuple(basis), microenterprise=micro)


def _nis2(annex: str | None, label: str, size: "_Size", cite: dict[str, Basis]) -> Regime:
    scope = cite["nis2_scope"]
    if annex is None:
        return Regime(
            "NIS2",
            Status.GILT_NICHT,
            (f"„{label}“ gehört zu keinem Sektor aus Anhang I oder II der NIS2.",),
            (scope,),
        )
    medium = size.is_medium_or_larger()
    size_basis = (cite["kmu_small"], cite["kmu_sme"])
    if medium is None:
        return Regime(
            "NIS2",
            Status.NICHT_BESTIMMBAR,
            (
                f"„{label}“ gehört zu Anhang {annex}. Für die Größe fehlen Angaben zu "
                "Beschäftigten, Umsatz oder Bilanzsumme.",
            ),
            (scope, *size_basis),
        )
    if not medium:
        return Regime(
            "NIS2",
            Status.GILT_NICHT,
            (f"„{label}“ gehört zu Anhang {annex}, das Unternehmen ist aber ein Klein- oder "
             "Kleinstunternehmen.",),
            (scope, *size_basis),
        )  # fmt: skip
    large = size.is_large()
    if annex == "I" and large:
        return Regime(
            "NIS2",
            Status.GILT,
            (f"„{label}“ gehört zu Anhang I, und das Unternehmen überschreitet die "
             "Schwellenwerte für mittlere Unternehmen: wesentliche Einrichtung.",),
            (scope, cite["nis2_essential"], cite["kmu_sme"]),
            EntityClass.WESENTLICH,
        )  # fmt: skip
    if annex == "I" and large is None:
        return Regime(
            "NIS2",
            Status.GILT,
            (f"„{label}“ gehört zu Anhang I. Ob das Unternehmen wesentliche oder wichtige "
             "Einrichtung ist, hängt von Angaben ab, die fehlen.",),
            (scope, cite["nis2_essential"], cite["nis2_important"], cite["kmu_sme"]),
        )  # fmt: skip
    return Regime(
        "NIS2",
        Status.GILT,
        (f"„{label}“ gehört zu Anhang {annex}, das Unternehmen ist mindestens mittelgroß: "
         "wichtige Einrichtung.",),
        (scope, cite["nis2_important"], *size_basis),
        EntityClass.WICHTIG,
    )  # fmt: skip


@dataclass(frozen=True)
class _Size:
    """Größenklasse nach der KMU-Empfehlung, mit drei Werten: ja, nein, unbekannt (None).

    „Jahresumsatz bzw. Jahresbilanz“ (Abs. 2 und 3) wird als „oder“ gelesen, wie in Abs. 1,
    der ausdrücklich „entweder … oder“ sagt: Ein Unternehmen ist klein, wenn es weniger als
    50 Personen beschäftigt und einer der beiden Werte höchstens 10 Mio. EUR beträgt.
    """

    employees: Decimal | None
    turnover: Decimal | None
    balance: Decimal | None

    def is_large(self) -> bool | None:
        """Überschreitet die Schwellenwerte für mittlere Unternehmen, ist also kein KMU."""
        sme = _all(
            _below(self.employees, 250),
            _any(_at_most(self.turnover, 50), _at_most(self.balance, 43)),
        )
        return None if sme is None else not sme

    def is_medium_or_larger(self) -> bool | None:
        small = _all(
            _below(self.employees, 50),
            _any(_at_most(self.turnover, 10), _at_most(self.balance, 10)),
        )
        return None if small is None else not small

    def is_dora_microenterprise(self) -> bool | None:
        return _all(
            _below(self.employees, 10),
            _any(_at_most(self.turnover, 2), _at_most(self.balance, 2)),
        )


def _number(value: AnswerValue | None) -> Decimal | None:
    return value if isinstance(value, Decimal) else None


def _below(value: Decimal | None, limit: int) -> bool | None:
    return None if value is None else value < limit


def _at_most(value: Decimal | None, limit: int) -> bool | None:
    return None if value is None else value <= limit


def _all(*values: bool | None) -> bool | None:
    if False in values:
        return False
    return None if None in values else True


def _any(*values: bool | None) -> bool | None:
    if True in values:
        return True
    return None if None in values else False


# ---------------------------------------------------------------- Hinweise


def question_hints(
    questionnaire: Questionnaire, answers: dict[str, AnswerValue], regulation: Regulation
) -> tuple[list[QuestionHint], list[str]]:
    """Pflichten aus den geltenden Gesetzen, die laut Fragebogen nicht erfüllt sind.

    Gibt die Hinweise und die Schlüssel der Pflichtfragen zurück, die noch offen sind.
    """
    laws = regulation.applicable_laws
    hints, unanswered = [], []
    for question in questionnaire.questions:
        basis = tuple(item for item in question.basis if item.law in laws)
        if not question.is_maturity or not basis:
            continue
        option = next((o for o in question.options if o.value == answers.get(question.key)), None)
        if option is None:
            unanswered.append(question.key)
        elif option.level < FULFILLED_LEVEL:
            severity = Severity.LUECKE if option.level == 0 else Severity.TEILWEISE
            hints.append(QuestionHint(question.key, question.text, option.label, severity, basis))
    return hints, unanswered


def inventory_hints(services: Sequence[AssessedService]) -> list[InventoryHint]:
    """DORA-Hinweise aus dem IT-Bestand. Sie gelten nur, wenn DORA gilt."""
    rules = load_rules()
    critical = [service for service in services if service.critical_function]
    hints = []

    without_exit = [service.name for service in critical if service.exit_plan is not True]
    if without_exit:
        hints.append(_inventory_hint(rules.hint("EXIT_PLAN_MISSING"), without_exit))

    by_group: dict[str, list[str]] = defaultdict(list)
    for service in critical:
        by_group[service.group].append(service.name)
    for group, names in sorted(by_group.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(names) >= 2:
            hints.append(_inventory_hint(rules.hint("CONCENTRATION"), names, group))

    hard = [service.name for service in critical if service.substitutability in HARD_TO_REPLACE]
    if hard:
        hints.append(_inventory_hint(rules.hint("HARD_TO_REPLACE"), hard))
    return hints


def _inventory_hint(
    rule: InventoryHintRule, services: list[str], group: str | None = None
) -> InventoryHint:
    return InventoryHint(
        rule.code, rule.title, rule.explanation, tuple(services), rule.basis, group
    )


def as_json(value: object) -> object:
    """Dataclasses, Gesetzesfundstellen und Wertelisten als JSON-taugliche Werte."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: as_json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple | list):
        return [as_json(item) for item in value]
    return value
