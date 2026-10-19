"""Roadmap: Fragen an die Anbieter, Maßnahmen, Priorität und drei Wellen."""

from datetime import date
from pathlib import Path

import pytest

from app.assessment import assess_inventory
from app.inventory import read_inventory
from app.models import Criticality, MigrationEffort
from app.roadmap import MeasureKind, build_roadmap
from app.seed import load_seed

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TODAY = date(2026, 10, 19)
HEADER = "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion\n"


@pytest.fixture
def roadmap_for(session):
    load_seed(session, DATA_DIR)

    def build(*lines: str):
        inventory = read_inventory((HEADER + "\n".join(lines) + "\n").encode(), "b.csv")
        assessment = assess_inventory(inventory.entries, session, TODAY)
        return build_roadmap(assessment, session, TODAY)

    return build


def test_every_gap_becomes_a_question_for_the_provider(roadmap_for):
    roadmap = roadmap_for("DATEV;Lohn;hoch;nein")

    facts = {question.fact for question in roadmap.questions}
    assert {"key_management", "operations_location", "data_export"} <= facts
    assert all(question.provider == "DATEV eG" for question in roadmap.questions)
    assert all(question.text.endswith("?") for question in roadmap.questions)


def test_question_states_how_far_a_favourable_answer_could_lift_the_service(roadmap_for):
    roadmap = roadmap_for("SWIFT;Zahlungsverkehr;hoch;ja")

    location = next(q for q in roadmap.questions if q.fact == "data_location")
    assert location.level_now == 0
    assert location.level_if_favourable >= location.level_now


def test_questions_are_ordered_by_criticality_then_gain(roadmap_for):
    roadmap = roadmap_for("Slack;Chat;gering;nein", "Okta;Anmeldung;hoch;ja")

    criticalities = [question.criticality for question in roadmap.questions]
    assert criticalities == sorted(criticalities, key=["HOCH", "MITTEL", "GERING"].index)


def test_better_variant_of_the_same_provider_is_proposed(roadmap_for):
    roadmap = roadmap_for("O365;E-Mail;hoch;nein")

    variants = [m for m in roadmap.measures if m.kind is MeasureKind.VARIANTE]
    assert [m.target for m in variants] == ["Delos Cloud (öffentliche Verwaltung)"]
    assert variants[0].potential_after > variants[0].potential_before


def test_eu_alternative_is_proposed_with_effort_from_the_database(roadmap_for):
    roadmap = roadmap_for("O365;E-Mail;hoch;nein")

    alternative = next(m for m in roadmap.measures if m.kind is MeasureKind.ALTERNATIVE)
    assert alternative.target == "Nextcloud"
    assert alternative.effort is MigrationEffort.HOCH
    assert alternative.wave == 3


def test_service_without_alternative_or_better_variant_gets_no_measure(roadmap_for):
    roadmap = roadmap_for("Slack;Chat;gering;nein")

    assert roadmap.measures == ()
    assert roadmap.questions


def test_measures_that_improve_nothing_are_left_out(roadmap_for):
    roadmap = roadmap_for("STACKIT;Test;gering;nein")

    assert all(
        m.level_after > m.level_before or m.potential_after > m.potential_before
        for m in roadmap.measures
    )


def test_wave_rules_are_low_effort_first_and_high_effort_last():
    from app.roadmap import WAVE_BY_EFFORT, WAVE_TITLES

    assert WAVE_BY_EFFORT == {
        MigrationEffort.GERING: 1,
        MigrationEffort.MITTEL: 2,
        MigrationEffort.HOCH: 3,
    }
    assert list(WAVE_TITLES) == [1, 2, 3]
    assert WAVE_TITLES[1].startswith("Schnelle Erfolge")
    assert WAVE_TITLES[3].startswith("Strategisch")


def test_roadmap_has_exactly_the_three_titled_waves(roadmap_for):
    from app.roadmap import WAVE_TITLES

    assert set(roadmap_for("Slack;Chat;gering;nein").waves) == set(WAVE_TITLES)


def test_waves_follow_effort(roadmap_for):
    roadmap = roadmap_for("O365;E-Mail;hoch;nein", "Okta;Anmeldung;hoch;ja")

    assert roadmap.waves[1], "Klärungen gehören in Welle 1"
    assert all(item.effort in (None, MigrationEffort.GERING) for item in roadmap.waves[1])
    assert all(item.effort is MigrationEffort.MITTEL for item in roadmap.waves[2])
    assert all(item.effort is MigrationEffort.HOCH for item in roadmap.waves[3])


def test_wave_items_are_ordered_by_priority(roadmap_for):
    roadmap = roadmap_for("Slack;Chat;gering;nein", "Okta;Anmeldung;hoch;ja")

    priorities = [item.priority for item in roadmap.waves[1]]
    assert priorities == sorted(priorities, reverse=True)


def test_priority_is_criticality_times_distance_to_top_level(roadmap_for):
    roadmap = roadmap_for("Okta;Anmeldung;hoch;ja")

    item = roadmap.waves[1][0]
    assert item.priority == 3 * (4 - item.level_now)
    assert item.criticality is Criticality.HOCH


def test_typical_mix_fills_all_three_waves(roadmap_for):
    roadmap = roadmap_for(
        "O365;E-Mail;hoch;nein", "AWS;Kundenportal;hoch;ja", "SWIFT;Zahlungen;hoch;ja"
    )

    assert roadmap.waves[1] and roadmap.waves[2] and roadmap.waves[3]


def test_core_questions_are_the_gaps_that_hold_the_overall_level_down(roadmap_for):
    roadmap = roadmap_for("SWIFT;Zahlungsverkehr;hoch;ja")

    core = {q.fact for q in roadmap.questions if q.is_core}
    others = {q.fact for q in roadmap.questions if not q.is_core}
    assert core == {"data_location"}
    assert "renewable_energy" in others


def test_wave_item_counts_core_questions_and_names_their_topics(roadmap_for):
    roadmap = roadmap_for("SWIFT;Zahlungsverkehr;hoch;ja")

    item = roadmap.waves[1][0]
    assert item.title == "Kernfrage an S.W.I.F.T. SC klären: Datenstandort"


def test_equal_priority_puts_the_larger_possible_gain_first(roadmap_for):
    roadmap = roadmap_for("Mastercard;Karten;hoch;ja", "SWIFT;Zahlungsverkehr;hoch;ja")

    first, second = roadmap.waves[1][:2]
    assert first.priority == second.priority
    assert first.possible_gain >= second.possible_gain


def test_measure_that_lowers_the_secured_level_explains_why(roadmap_for):
    roadmap = roadmap_for("AWS;Kundenportal;hoch;ja")

    sovereign = next(m for m in roadmap.measures if m.target == "AWS European Sovereign Cloud")
    assert sovereign.level_after < sovereign.level_before
    assert "Angaben zur Zielvariante fehlen" in sovereign.note
