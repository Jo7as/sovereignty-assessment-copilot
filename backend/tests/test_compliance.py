from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.assessment import _exit_plan, _hardest
from app.compliance import (
    EntityClass,
    Severity,
    Status,
    determine_regulation,
    inventory_hints,
    load_rules,
    question_hints,
)
from app.questionnaire import load_questionnaire

QUESTIONNAIRE = load_questionnaire()


def regulation(sector=None, employees=None, turnover=None, balance=None):
    answers = {"sector": sector}
    for key, value in [
        ("employees", employees),
        ("annual_turnover", turnover),
        ("balance_sheet_total", balance),
    ]:
        if value is not None:
            answers[key] = Decimal(str(value))
    return determine_regulation(QUESTIONNAIRE, {k: v for k, v in answers.items() if v})


def articles(regime) -> list[str]:
    return [f"{basis.law} {basis.article}" for basis in regime.basis]


# ---------------------------------------------------------------- Welches Recht gilt


def test_without_sector_nothing_can_be_determined():
    result = regulation()

    assert (result.dora.status, result.nis2.status) == (Status.NICHT_BESTIMMBAR,) * 2
    assert result.applicable_laws == frozenset()


def test_large_bank_is_essential_under_nis2_but_dora_precedes():
    result = regulation("KREDITINSTITUT", employees=400)

    assert result.dora.status is Status.GILT
    assert (result.nis2.status, result.nis2.entity_class) == (Status.GILT, EntityClass.WESENTLICH)
    assert result.dora_precedes_nis2
    assert result.applicable_laws == {"DORA"}
    assert "DORA Art. 1 Abs. 2" in articles(result.nis2)
    assert "NIS2 Art. 4 Abs. 1" in articles(result.nis2)


def test_bank_with_low_turnover_is_an_sme_despite_a_large_balance_sheet():
    """KMU: unter 250 Beschäftigte und entweder Umsatz bis 50 oder Bilanzsumme bis 43 Mio."""
    result = regulation("KREDITINSTITUT", employees=180, turnover=40, balance=2500)

    assert result.nis2.entity_class is EntityClass.WICHTIG


def test_exceeding_both_financial_thresholds_makes_an_entity_large():
    result = regulation("ENERGIE", employees=200, turnover=60, balance=50)

    assert result.nis2.entity_class is EntityClass.WESENTLICH


@pytest.mark.parametrize(
    ("employees", "expected"), [(249, EntityClass.WICHTIG), (250, EntityClass.WESENTLICH)]
)
def test_250_employees_is_the_threshold_for_large(employees, expected):
    result = regulation("ENERGIE", employees=employees, turnover=20, balance=20)

    assert result.nis2.entity_class is expected


@pytest.mark.parametrize(("turnover", "balance"), [(50, 100), (100, 43)])
def test_turnover_of_exactly_50_or_balance_of_exactly_43_still_counts_as_sme(turnover, balance):
    result = regulation("ENERGIE", employees=200, turnover=turnover, balance=balance)

    assert result.nis2.entity_class is EntityClass.WICHTIG


def test_annex_one_without_financial_figures_leaves_the_class_open():
    result = regulation("ENERGIE", employees=120)

    assert (result.nis2.status, result.nis2.entity_class) == (Status.GILT, None)
    assert result.applicable_laws == {"NIS2"}


def test_annex_two_is_never_essential():
    result = regulation("VERARBEITENDES_GEWERBE", employees=5000)

    assert result.nis2.entity_class is EntityClass.WICHTIG


@pytest.mark.parametrize(
    ("employees", "turnover", "balance", "status"),
    [
        (30, 12, 8, Status.GILT_NICHT),  # klein: Bilanzsumme bis 10 Mio.
        (30, 10, 11, Status.GILT_NICHT),  # klein: Umsatz genau 10 Mio.
        (30, 11, 10, Status.GILT_NICHT),  # klein: Bilanzsumme genau 10 Mio.
        (30, 12, 11, Status.GILT),  # beide Werte über 10 Mio.: mittelgroß
        (50, 1, 1, Status.GILT),  # genau 50 Beschäftigte: nicht mehr klein
        (30, None, None, Status.NICHT_BESTIMMBAR),
    ],
)
def test_small_enterprises_are_outside_nis2(employees, turnover, balance, status):
    result = regulation("VERARBEITENDES_GEWERBE", employees, turnover, balance)

    assert result.nis2.status is status


def test_payment_institution_falls_under_dora_only():
    result = regulation("ZAHLUNGSINSTITUT", employees=80)

    assert (result.dora.status, result.nis2.status) == (Status.GILT, Status.GILT_NICHT)
    assert not result.dora_precedes_nis2


def test_other_sector_falls_under_neither():
    result = regulation("ANDERER", employees=5000)

    assert (result.dora.status, result.nis2.status) == (Status.GILT_NICHT, Status.GILT_NICHT)


def test_dora_microenterprise_is_recognised_with_its_definition():
    result = regulation("ZAHLUNGSINSTITUT", employees=8, turnover=1.5)

    assert result.dora.microenterprise is True
    assert "DORA Art. 3 Nr. 60" in articles(result.dora)


def test_ten_employees_are_no_longer_a_dora_microenterprise():
    assert regulation("ZAHLUNGSINSTITUT", employees=10, turnover=1).dora.microenterprise is False


def test_dora_microenterprise_stays_open_without_figures():
    assert regulation("ZAHLUNGSINSTITUT", employees=8).dora.microenterprise is None


def test_every_regime_cites_its_legal_basis():
    for sector in ["KREDITINSTITUT", "ENERGIE", "ANDERER"]:
        result = regulation(sector, employees=100, turnover=20, balance=20)
        assert result.dora.basis and result.nis2.basis


# ---------------------------------------------------------------- Hinweise aus dem Fragebogen


def hints_for(sector_answers: dict, answers: dict):
    result = determine_regulation(QUESTIONNAIRE, sector_answers)
    return question_hints(QUESTIONNAIRE, {**sector_answers, **answers}, result)


BANK = {"sector": "KREDITINSTITUT"}
ENERGY = {"sector": "ENERGIE", "employees": Decimal(120)}


def test_missing_exit_strategy_is_a_gap_under_dora():
    hints, _ = hints_for(BANK, {"exit_strategy": "NEIN"})

    assert [(h.question, h.severity) for h in hints] == [("exit_strategy", Severity.LUECKE)]
    assert [basis.article for basis in hints[0].basis] == ["Art. 28 Abs. 8"]


@pytest.mark.parametrize(
    ("answer", "severity"),
    [("UNBEKANNT", Severity.LUECKE), ("EINIGE", Severity.TEILWEISE), ("ALLE", None)],
)
def test_severity_follows_the_level(answer, severity):
    hints, _ = hints_for(BANK, {"exit_strategy": answer})

    assert [h.severity for h in hints] == ([severity] if severity else [])


def test_nis2_only_entity_gets_nis2_hints_and_no_dora_hints():
    hints, unanswered = hints_for(ENERGY, {"management_training": "NEIN", "exit_strategy": "NEIN"})

    assert [h.question for h in hints] == ["management_training"]
    assert {basis.law for basis in hints[0].basis} == {"NIS2"}
    assert "exit_strategy" not in unanswered


def test_bank_gets_no_nis2_hints_because_dora_precedes():
    sector = {**BANK, "employees": Decimal(400)}

    hints, unanswered = hints_for(sector, {"management_training": "NEIN"})

    assert hints == []
    assert "management_training" not in unanswered


def test_no_hints_without_applicable_law():
    hints, unanswered = hints_for({"sector": "ANDERER"}, {"exit_strategy": "NEIN"})

    assert (hints, unanswered) == ([], [])


def test_open_obligations_are_listed_separately():
    _, unanswered = hints_for(BANK, {"exit_strategy": "NEIN"})

    assert "exit_tested" in unanswered
    assert "exit_strategy" not in unanswered
    assert "sovereignty_goals" not in unanswered  # ohne Rechtsgrundlage keine Pflicht


# ---------------------------------------------------------------- Hinweise aus dem IT-Bestand


def service(name, group="Anbieter", critical=True, exit_plan=False, substitutability=None):
    return SimpleNamespace(
        name=name,
        group=group,
        critical_function=critical,
        exit_plan=exit_plan,
        substitutability=substitutability,
    )


def codes(hints) -> list[str]:
    return [hint.code for hint in hints]


def test_critical_services_without_exit_plan_are_listed():
    hints = inventory_hints(
        [
            service("Kernbank", group="A", exit_plan=False),
            service("Zahlungsverkehr", group="B", exit_plan=None),
            service("Meldewesen", group="C", exit_plan=True),
            service("Wiki", group="D", critical=False, exit_plan=False),
        ]
    )

    assert codes(hints) == ["EXIT_PLAN_MISSING"]
    assert hints[0].services == ("Kernbank", "Zahlungsverkehr")
    assert hints[0].basis[0].article == "Art. 28 Abs. 8"


def test_two_critical_services_of_one_group_are_a_concentration():
    hints = inventory_hints(
        [
            service("Azure", group="Microsoft Corporation", exit_plan=True),
            service("GitHub", group="Microsoft Corporation", exit_plan=True),
            service("Kernbank", group="Avaloq", exit_plan=True),
            service("Teams", group="Microsoft Corporation", critical=False, exit_plan=True),
        ]
    )

    assert codes(hints) == ["CONCENTRATION"]
    assert (hints[0].group, hints[0].services) == ("Microsoft Corporation", ("Azure", "GitHub"))


def test_largest_concentration_comes_first():
    hints = inventory_hints(
        [service(name, group="B", exit_plan=True) for name in ["b1", "b2"]]
        + [service(name, group="A", exit_plan=True) for name in ["a1", "a2", "a3"]]
    )

    assert [hint.group for hint in hints] == ["A", "B"]


def test_hard_to_replace_includes_very_complex_but_not_medium():
    hints = inventory_hints(
        [
            service("SWIFT", group="A", exit_plan=True, substitutability="nicht ersetzbar"),
            service("Avaloq", group="B", exit_plan=True, substitutability="sehr komplex"),
            service("Slack", group="C", exit_plan=True, substitutability="mittel"),
        ]
    )

    assert codes(hints) == ["HARD_TO_REPLACE"]
    assert hints[0].services == ("SWIFT", "Avaloq")


def test_without_critical_services_there_are_no_hints():
    assert inventory_hints([service("Wiki", critical=False)]) == []


def test_every_inventory_rule_cites_dora():
    for rule in load_rules().inventory_hints:
        assert {basis.law for basis in rule.basis} == {"DORA"}


# ---------------------------------------------------------------- Zusammenfassen mehrerer Einträge


@pytest.mark.parametrize(
    ("values", "expected"),
    [([True, True], True), ([True, False], False), ([True, None], None), ([], None)],
)
def test_exit_plan_counts_only_if_every_entry_names_it(values, expected):
    assert _exit_plan(values) is expected


def test_hardest_substitutability_wins():
    assert _hardest(["leicht", None, "sehr komplex", "mittel"]) == "sehr komplex"
    assert _hardest([None]) is None
