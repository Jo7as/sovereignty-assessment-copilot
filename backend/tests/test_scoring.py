"""Regeln der Bewertungslogik. Erklärt in docs/bewertungslogik.md."""

import random
from dataclasses import fields, replace
from datetime import date

import pytest

from app.models import (
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
)
from app.scoring import (
    WEIGHTS,
    CertificateFact,
    DependencyFact,
    Objective,
    VariantFacts,
    assess,
)

TODAY = date(2026, 10, 13)
EU, USA, ADEQUATE = Jurisdiction.EU_EWR, Jurisdiction.USA, Jurisdiction.ANGEMESSEN

C5 = CertificateFact("bsi-c5")
ISO = CertificateFact("iso-27001")


def dependency(jurisdiction=USA, critical=True, kind=DependencyKind.HOSTING) -> DependencyFact:
    return DependencyFact("Zulieferer", jurisdiction, kind, critical)


def sovereign(**changes) -> VariantFacts:
    """Vollständig europäischer Dienst ohne Schwächen: Ausgangspunkt jeder Regelprüfung."""
    facts = VariantFacts(
        provider_jurisdiction=EU,
        operator_jurisdiction=None,
        operator_seat=None,
        data_location=DataLocation.EU_ZUGESICHERT,
        operations_location=OperationsLocation.NUR_EU,
        transfer_basis=TransferBasis.NICHT_NOETIG,
        governing_law=EU,
        key_management=KeyManagement.KUNDE_EXTERN,
        data_export=DataExport.OFFENE_FORMATE,
        openness=Openness.OPEN_SOURCE,
        ai_training=AiTraining.NEIN,
        renewable_energy=RenewableEnergy.NACHGEWIESEN,
        certificates=(C5, ISO),
        dependencies=(),
        dependencies_complete=True,
    )
    return replace(facts, **changes)


def us_provider(**changes) -> VariantFacts:
    """US-Anbieter mit den besten Schutzmaßnahmen, aber ohne EU-Betriebsgesellschaft."""
    defaults = {
        "provider_jurisdiction": USA,
        "transfer_basis": TransferBasis.STANDARDVERTRAGSKLAUSELN,
        "openness": Openness.PROPRIETAER,
    }
    return sovereign(**(defaults | changes))


def level(facts: VariantFacts, objective: Objective) -> int:
    return assess(facts, TODAY).objectives[objective].level


def potential(facts: VariantFacts, objective: Objective) -> int:
    return assess(facts, TODAY).objectives[objective].potential


# --- Die fünf Stufen aus der CLAUDE.md -----------------------------------------------


def test_level_4_fully_european_service():
    result = assess(sovereign(), TODAY)

    assert result.level == 4
    assert result.potential == 4
    assert result.score == 100
    assert result.gaps == ()


def test_level_3_eu_provider_with_single_non_eu_dependency():
    result = assess(sovereign(dependencies=(dependency(critical=False),)), TODAY)

    assert result.level == 3


def test_level_2_non_eu_provider_with_eu_operating_company_own_keys_and_exit():
    facts = us_provider(operator_jurisdiction=USA, operator_seat=EU)

    assert assess(facts, TODAY).level == 2


def test_level_1_non_eu_provider_with_eu_data_centre_and_contract_clauses():
    facts = us_provider(
        data_location=DataLocation.EU_WAEHLBAR,
        key_management=KeyManagement.ANBIETER,
        operations_location=OperationsLocation.WELTWEIT,
    )

    assert assess(facts, TODAY).level == 1


def test_level_0_non_eu_provider_without_protection():
    facts = us_provider(
        data_location=DataLocation.NICHT_EU, transfer_basis=TransferBasis.KEINE, governing_law=USA
    )

    assert assess(facts, TODAY).level == 0


# --- Gesamtergebnis --------------------------------------------------------------------


def test_overall_level_is_the_weakest_objective():
    result = assess(sovereign(renewable_energy=RenewableEnergy.ZUGESAGT), TODAY)

    assert result.objectives[Objective.UMWELT].level == 2
    assert result.level == 2
    assert result.weakest == (Objective.UMWELT,)


def test_score_weights_objectives_as_the_eu_framework_does():
    # Abschnitt 5 des EU Cloud Sovereignty Framework, Version 1.2.1
    assert WEIGHTS == {
        Objective.STRATEGISCH: 15,
        Objective.RECHTLICH: 10,
        Objective.DATEN_KI: 10,
        Objective.OPERATIV: 15,
        Objective.LIEFERKETTE: 20,
        Objective.TECHNOLOGIE: 15,
        Objective.SICHERHEIT: 10,
        Objective.UMWELT: 5,
    }
    assert sum(WEIGHTS.values()) == 100

    result = assess(sovereign(renewable_energy=RenewableEnergy.ZUGESAGT), TODAY)

    # Umwelt zählt 5 Prozent, Stufe 2 von 4 kostet davon die Hälfte
    assert result.score == 97.5


def test_every_objective_names_the_finding_that_limits_it():
    result = assess(sovereign(data_export=DataExport.KEIN_EXPORT), TODAY)

    limiting = result.objectives[Objective.OPERATIV].limiting

    assert [finding.fact for finding in limiting] == ["data_export"]
    assert "Export" in limiting[0].reason


# --- Unbekannte Angaben ----------------------------------------------------------------


def test_unknown_fact_counts_as_worst_case_but_keeps_the_potential():
    result = assess(sovereign(data_location=DataLocation.UNBEKANNT), TODAY)

    data = result.objectives[Objective.DATEN_KI]
    assert (data.level, data.potential) == (0, 4)
    assert (result.level, result.potential) == (0, 4)
    assert result.gaps == ("data_location",)
    assert result.is_provisional


def test_unknown_facts_of_an_empty_entry_are_all_listed_as_gaps():
    empty = sovereign(
        data_location=DataLocation.UNBEKANNT,
        operations_location=OperationsLocation.UNBEKANNT,
        transfer_basis=TransferBasis.UNBEKANNT,
        governing_law=None,
        key_management=KeyManagement.UNBEKANNT,
        data_export=DataExport.UNBEKANNT,
        openness=Openness.UNBEKANNT,
        ai_training=AiTraining.UNBEKANNT,
        renewable_energy=RenewableEnergy.KEINE_ANGABE,
        certificates=(),
        dependencies_complete=False,
    )

    assert assess(empty, TODAY).gaps == (
        "ai_training_on_customer_data",
        "certificates",
        "data_export",
        "data_location",
        "dependencies",
        "governing_law",
        "key_management",
        "openness",
        "operations_location",
        "renewable_energy",
        "transfer_basis",
    )


UNKNOWN_VALUES = {
    "data_location": (DataLocation.UNBEKANNT, DataLocation),
    "operations_location": (OperationsLocation.UNBEKANNT, OperationsLocation),
    "transfer_basis": (TransferBasis.UNBEKANNT, TransferBasis),
    "key_management": (KeyManagement.UNBEKANNT, KeyManagement),
    "data_export": (DataExport.UNBEKANNT, DataExport),
    "openness": (Openness.UNBEKANNT, Openness),
    "ai_training": (AiTraining.UNBEKANNT, AiTraining),
    "renewable_energy": (RenewableEnergy.KEINE_ANGABE, RenewableEnergy),
    "governing_law": (None, (EU, USA, ADEQUATE, Jurisdiction.DRITTSTAAT)),
}


def random_facts(rng: random.Random) -> VariantFacts:
    jurisdictions = list(Jurisdiction)
    has_operator = rng.random() < 0.4
    return VariantFacts(
        provider_jurisdiction=rng.choice(jurisdictions),
        operator_jurisdiction=rng.choice(jurisdictions) if has_operator else None,
        operator_seat=rng.choice(jurisdictions) if has_operator else None,
        data_location=rng.choice(list(DataLocation)),
        operations_location=rng.choice(list(OperationsLocation)),
        transfer_basis=rng.choice(list(TransferBasis)),
        governing_law=rng.choice([None, *jurisdictions]),
        key_management=rng.choice(list(KeyManagement)),
        data_export=rng.choice(list(DataExport)),
        openness=rng.choice(list(Openness)),
        ai_training=rng.choice(list(AiTraining)),
        renewable_energy=rng.choice(list(RenewableEnergy)),
        certificates=tuple(rng.sample([C5, ISO], rng.randint(0, 2))),
        dependencies=tuple(
            dependency(
                rng.choice(jurisdictions), rng.random() < 0.5, rng.choice(list(DependencyKind))
            )
            for _ in range(rng.randint(0, 2))
        ),
        dependencies_complete=rng.random() < 0.5,
    )


def test_levels_stay_within_bounds_for_any_combination_of_facts():
    rng = random.Random(20261013)
    for _ in range(3000):
        result = assess(random_facts(rng), TODAY)
        for objective in result.objectives.values():
            assert 0 <= objective.level <= objective.potential <= 4
        assert 0 <= result.level <= result.potential <= 4
        assert 0 <= result.score <= result.potential_score <= 100


def test_resolving_an_unknown_fact_always_lands_between_level_and_potential():
    """Die Spanne aus gesicherter und möglicher Stufe ist eine echte Schranke."""
    rng = random.Random(42)
    checked = 0
    for _ in range(1500):
        facts = random_facts(rng)
        before = assess(facts, TODAY)
        for name, (unknown, known_values) in UNKNOWN_VALUES.items():
            if getattr(facts, name) != unknown:
                continue
            for value in known_values:
                if value == unknown:
                    continue
                after = assess(replace(facts, **{name: value}), TODAY)
                assert before.level <= after.level <= after.potential <= before.potential
                for objective, old in before.objectives.items():
                    new = after.objectives[objective]
                    assert old.level <= new.level <= new.potential <= old.potential
                checked += 1
    assert checked > 5000


def test_recording_the_supply_chain_as_complete_lands_between_level_and_potential():
    rng = random.Random(7)
    for _ in range(1500):
        facts = replace(random_facts(rng), dependencies_complete=False)
        before = assess(facts, TODAY)
        after = assess(replace(facts, dependencies_complete=True), TODAY)
        assert before.level <= after.level <= after.potential <= before.potential


# --- Strategisch -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, 4),
        ({"provider_jurisdiction": ADEQUATE}, 3),
        ({"provider_jurisdiction": USA}, 1),
        ({"provider_jurisdiction": Jurisdiction.DRITTSTAAT}, 1),
        ({"provider_jurisdiction": USA, "operator_jurisdiction": USA, "operator_seat": EU}, 2),
        ({"provider_jurisdiction": USA, "operator_jurisdiction": USA, "operator_seat": USA}, 1),
        # Ein Betreiber unter EU-Kontrolle hat die Entscheidungsgewalt, auch bei US-Technologie
        ({"provider_jurisdiction": USA, "operator_jurisdiction": EU, "operator_seat": EU}, 4),
        # Ein Betreiber unter US-Kontrolle nimmt sie einem EU-Anbieter
        ({"operator_jurisdiction": USA, "operator_seat": EU}, 2),
        # Ein Betreiber mit Sitz in den USA untersteht US-Recht, auch mit EU-Konzernmutter
        ({"operator_jurisdiction": EU, "operator_seat": USA}, 1),
        ({"operator_jurisdiction": EU, "operator_seat": ADEQUATE}, 3),
        ({"operator_jurisdiction": EU, "operator_seat": Jurisdiction.DRITTSTAAT}, 1),
        ({"operator_jurisdiction": ADEQUATE, "operator_seat": USA}, 1),
        ({"operator_jurisdiction": ADEQUATE, "operator_seat": Jurisdiction.DRITTSTAAT}, 1),
        ({"operator_jurisdiction": Jurisdiction.DRITTSTAAT, "operator_seat": ADEQUATE}, 1),
    ],
)
def test_strategic_level_follows_who_controls_the_service(changes, expected):
    assert level(sovereign(**changes), Objective.STRATEGISCH) == expected


def test_strategic_level_drops_when_service_cannot_continue_without_non_eu_supplier():
    facts = sovereign(dependencies=(dependency(critical=True),))

    assert level(facts, Objective.STRATEGISCH) == 3


# --- Rechtlich -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("transfer_basis", "expected"),
    [
        (TransferBasis.STANDARDVERTRAGSKLAUSELN, 1),
        (TransferBasis.DATA_PRIVACY_FRAMEWORK, 1),
        (TransferBasis.KEINE, 0),
        (TransferBasis.UNBEKANNT, 0),
    ],
)
def test_non_eu_provider_needs_a_transfer_basis(transfer_basis, expected):
    assert level(us_provider(transfer_basis=transfer_basis), Objective.RECHTLICH) == expected


def test_transfer_basis_is_irrelevant_for_eu_provider_with_data_in_the_eu():
    facts = sovereign(transfer_basis=TransferBasis.UNBEKANNT)

    assert level(facts, Objective.RECHTLICH) == 4
    assert assess(facts, TODAY).gaps == ()


def test_transfer_basis_matters_for_eu_provider_storing_data_outside_the_eu():
    facts = sovereign(data_location=DataLocation.NICHT_EU, transfer_basis=TransferBasis.KEINE)

    assert level(facts, Objective.RECHTLICH) == 0


@pytest.mark.parametrize(("law", "expected"), [(EU, 4), (ADEQUATE, 3), (USA, 1), (None, 1)])
def test_governing_law_outside_the_eu_limits_the_legal_level(law, expected):
    assert level(sovereign(governing_law=law), Objective.RECHTLICH) == expected


# --- Daten und KI ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (DataLocation.EU_ZUGESICHERT, 4),
        (DataLocation.EU_WAEHLBAR, 3),
        (DataLocation.NICHT_EU, 0),
        (DataLocation.UNBEKANNT, 0),
    ],
)
def test_data_location(location, expected):
    assert level(sovereign(data_location=location), Objective.DATEN_KI) == expected


@pytest.mark.parametrize(
    ("provider", "keys", "expected"),
    [
        (EU, KeyManagement.KUNDE_EXTERN, 4),
        (EU, KeyManagement.KUNDE_BEIM_ANBIETER, 4),
        (EU, KeyManagement.ANBIETER, 3),
        (EU, KeyManagement.UNBEKANNT, 3),
        (ADEQUATE, KeyManagement.KUNDE_EXTERN, 4),
        (ADEQUATE, KeyManagement.KUNDE_BEIM_ANBIETER, 3),
        (ADEQUATE, KeyManagement.ANBIETER, 2),
        (USA, KeyManagement.KUNDE_EXTERN, 4),
        (USA, KeyManagement.KUNDE_BEIM_ANBIETER, 2),
        (USA, KeyManagement.ANBIETER, 1),
        (USA, KeyManagement.UNBEKANNT, 1),
    ],
)
def test_key_management_depends_on_who_could_be_compelled_to_hand_over_keys(
    provider, keys, expected
):
    facts = sovereign(provider_jurisdiction=provider, key_management=keys)

    assert level(facts, Objective.DATEN_KI) == expected


@pytest.mark.parametrize(
    ("training", "expected"),
    [
        (AiTraining.NEIN, 4),
        (AiTraining.ABWAEHLBAR, 3),
        (AiTraining.JA, 1),
        (AiTraining.UNBEKANNT, 1),
    ],
)
def test_ai_training_on_customer_data(training, expected):
    assert level(sovereign(ai_training=training), Objective.DATEN_KI) == expected


# --- Operativ --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("operations", "expected"),
    [
        (OperationsLocation.NUR_EU, 4),
        (OperationsLocation.EU_MIT_AUSNAHMEN, 2),
        (OperationsLocation.WELTWEIT, 1),
        (OperationsLocation.UNBEKANNT, 1),
    ],
)
def test_operations_location(operations, expected):
    assert level(sovereign(operations_location=operations), Objective.OPERATIV) == expected


@pytest.mark.parametrize(
    ("export", "expected"),
    [
        (DataExport.OFFENE_FORMATE, 4),
        (DataExport.PROPRIETAER, 2),
        (DataExport.KEIN_EXPORT, 1),
        (DataExport.UNBEKANNT, 1),
    ],
)
def test_data_export(export, expected):
    assert level(sovereign(data_export=export), Objective.OPERATIV) == expected


def test_critical_non_eu_supplier_limits_operations():
    assert level(sovereign(dependencies=(dependency(critical=True),)), Objective.OPERATIV) == 2


def test_non_critical_non_eu_supplier_does_not_limit_operations():
    assert level(sovereign(dependencies=(dependency(critical=False),)), Objective.OPERATIV) == 4


# --- Lieferkette -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dependencies", "complete", "expected_level", "expected_potential"),
    [
        ((), True, 4, 4),
        ((dependency(EU, critical=True),), True, 4, 4),
        ((dependency(USA, critical=False),), True, 3, 3),
        ((dependency(ADEQUATE, critical=False),), True, 3, 3),
        ((dependency(USA, critical=True),), True, 2, 2),
        ((dependency(USA, critical=True),), False, 2, 2),
        # Ohne geprüfte Lieferkette ist ein kritischer Nicht-EU-Zulieferer nicht auszuschließen
        ((), False, 2, 4),
        ((dependency(USA, critical=False),), False, 2, 3),
    ],
)
def test_supply_chain_dependencies(dependencies, complete, expected_level, expected_potential):
    facts = sovereign(dependencies=dependencies, dependencies_complete=complete)

    assert level(facts, Objective.LIEFERKETTE) == expected_level
    assert potential(facts, Objective.LIEFERKETTE) == expected_potential


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"provider_jurisdiction": USA}, 1),
        ({"provider_jurisdiction": USA, "operator_jurisdiction": USA, "operator_seat": EU}, 2),
        # Die Technologie bleibt aus den USA, auch wenn ein EU-Unternehmen sie betreibt
        ({"provider_jurisdiction": USA, "operator_jurisdiction": EU, "operator_seat": EU}, 2),
    ],
)
def test_supply_chain_reflects_where_the_technology_comes_from(changes, expected):
    assert level(sovereign(**changes), Objective.LIEFERKETTE) == expected


# --- Technologie -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("provider", "openness", "expected"),
    [
        (EU, Openness.OPEN_SOURCE, 4),
        (EU, Openness.OFFENE_STANDARDS, 4),
        (EU, Openness.PROPRIETAER, 3),
        (EU, Openness.UNBEKANNT, 3),
        (ADEQUATE, Openness.OFFENE_STANDARDS, 3),
        (ADEQUATE, Openness.PROPRIETAER, 3),
        (USA, Openness.OPEN_SOURCE, 4),
        (USA, Openness.OFFENE_STANDARDS, 2),
        (USA, Openness.PROPRIETAER, 1),
        (USA, Openness.UNBEKANNT, 1),
    ],
)
def test_technology_level_combines_openness_and_origin(provider, openness, expected):
    facts = sovereign(provider_jurisdiction=provider, openness=openness)

    assert level(facts, Objective.TECHNOLOGIE) == expected


def test_proprietary_non_eu_technology_with_eu_operating_company():
    facts = us_provider(operator_jurisdiction=EU, operator_seat=EU)

    assert level(facts, Objective.TECHNOLOGIE) == 2


def test_critical_non_eu_technology_dependency_limits_technology():
    technology = dependency(critical=True, kind=DependencyKind.TECHNOLOGIE)
    hosting = dependency(critical=True, kind=DependencyKind.HOSTING)

    assert level(sovereign(dependencies=(technology,)), Objective.TECHNOLOGIE) == 2
    assert level(sovereign(dependencies=(hosting,)), Objective.TECHNOLOGIE) == 4


# --- Sicherheit und Compliance ---------------------------------------------------------


@pytest.mark.parametrize(
    ("certificates", "expected_level", "expected_potential"),
    [
        ((C5, ISO), 4, 4),
        ((C5,), 4, 4),
        ((ISO,), 3, 3),
        ((), 1, 4),
        ((CertificateFact("bsi-c5", date(2026, 10, 13)),), 4, 4),
        ((CertificateFact("bsi-c5", date(2026, 10, 12)),), 1, 4),
        ((CertificateFact("bsi-c5", date(2026, 10, 12)), ISO), 3, 3),
    ],
)
def test_certificates(certificates, expected_level, expected_potential):
    facts = sovereign(certificates=certificates)

    assert level(facts, Objective.SICHERHEIT) == expected_level
    assert potential(facts, Objective.SICHERHEIT) == expected_potential


def test_certificate_does_not_lift_security_operations_under_non_eu_control():
    assert level(us_provider(), Objective.SICHERHEIT) == 1


# --- Umwelt ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("renewable", "expected_level", "expected_potential"),
    [
        (RenewableEnergy.NACHGEWIESEN, 4, 4),
        (RenewableEnergy.ZUGESAGT, 2, 2),
        (RenewableEnergy.KEINE_ANGABE, 0, 4),
    ],
)
def test_renewable_energy(renewable, expected_level, expected_potential):
    facts = sovereign(renewable_energy=renewable)

    assert level(facts, Objective.UMWELT) == expected_level
    assert potential(facts, Objective.UMWELT) == expected_potential


# --- Bessere Angaben verschlechtern nie ------------------------------------------------

ORDERED_FROM_WORST_TO_BEST = {
    "data_location": [DataLocation.NICHT_EU, DataLocation.EU_WAEHLBAR, DataLocation.EU_ZUGESICHERT],
    "operations_location": [
        OperationsLocation.WELTWEIT,
        OperationsLocation.EU_MIT_AUSNAHMEN,
        OperationsLocation.NUR_EU,
    ],
    "key_management": [
        KeyManagement.ANBIETER,
        KeyManagement.KUNDE_BEIM_ANBIETER,
        KeyManagement.KUNDE_EXTERN,
    ],
    "data_export": [DataExport.KEIN_EXPORT, DataExport.PROPRIETAER, DataExport.OFFENE_FORMATE],
    "openness": [Openness.PROPRIETAER, Openness.OFFENE_STANDARDS, Openness.OPEN_SOURCE],
    "ai_training": [AiTraining.JA, AiTraining.ABWAEHLBAR, AiTraining.NEIN],
    "renewable_energy": [RenewableEnergy.ZUGESAGT, RenewableEnergy.NACHGEWIESEN],
    "provider_jurisdiction": [USA, ADEQUATE, EU],
    "governing_law": [USA, ADEQUATE, EU],
}


def test_a_better_fact_never_lowers_any_level():
    rng = random.Random(99)
    for _ in range(800):
        facts = random_facts(rng)
        for name, ordered in ORDERED_FROM_WORST_TO_BEST.items():
            results = [assess(replace(facts, **{name: value}), TODAY) for value in ordered]
            for worse, better in zip(results, results[1:], strict=False):
                assert worse.level <= better.level
                assert worse.score <= better.score


def test_property_tests_cover_every_fact():
    """Schlägt fehl, wenn ein neues Merkmal dazukommt und in den Prüfungen oben fehlt."""
    covered = set(UNKNOWN_VALUES) | set(ORDERED_FROM_WORST_TO_BEST)
    structural = {
        "operator_jurisdiction",
        "operator_seat",
        "certificates",
        "dependencies",
        "dependencies_complete",
    }

    assert {field.name for field in fields(VariantFacts)} == covered | structural
