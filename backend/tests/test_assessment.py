"""Bewertung eines IT-Bestands: Zuordnung, Zusammenfassung je Dienst und Gesamtwert."""

from datetime import date
from pathlib import Path

import pytest

from app.assessment import assess_inventory
from app.inventory import read_inventory
from app.models import Criticality
from app.seed import load_seed

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TODAY = date(2026, 10, 19)
HEADER = "Dienst;Variante;Zweck;Kritikalität;Kritische oder wichtige Funktion\n"


@pytest.fixture
def seeded(session):
    load_seed(session, DATA_DIR)
    return session


def entries(*lines: str):
    result = read_inventory((HEADER + "\n".join(lines) + "\n").encode(), "bestand.csv")
    assert result.errors == []
    return result.entries


def test_several_entries_of_one_service_are_counted_once_with_highest_criticality(seeded):
    result = assess_inventory(
        entries(
            "O365;;E-Mail;mittel;nein",
            "Teams Telefonie;;Telefonie;hoch;nein",
            "Exchange Online;;E-Mail;gering;ja",
        ),
        seeded,
        TODAY,
    )

    assert [service.slug for service in result.services] == ["microsoft-365"]
    service = result.services[0]
    assert service.criticality is Criticality.HOCH
    assert service.critical_function is True
    assert service.rows == (2, 3, 4)


def test_default_variant_is_used_without_variant_text(seeded):
    result = assess_inventory(entries("GitHub;;Quellcode;mittel;nein"), seeded, TODAY)

    assert result.services[0].variant_slug == "standard"


def test_variant_text_selects_the_matching_variant(seeded):
    result = assess_inventory(
        entries("GitHub Enterprise Cloud;mit Datenresidenz EU;Quellcode;mittel;nein"), seeded, TODAY
    )

    assert result.services[0].variant_slug == "data-residency"


def test_unknown_variant_text_falls_back_to_default_with_a_note(seeded):
    result = assess_inventory(entries("GitHub;Sonderedition;Quellcode;mittel;nein"), seeded, TODAY)

    service = result.services[0]
    assert service.variant_slug == "standard"
    assert "Sonderedition" in service.notes[0]


def test_unmatched_entries_are_listed_but_not_assessed(seeded):
    result = assess_inventory(
        entries("EBICS-Server;;Zahlungsverkehr;hoch;ja", "Slack;;Chat;gering;nein"), seeded, TODAY
    )

    assert [service.slug for service in result.services] == ["slack"]
    assert [(entry.row, entry.service) for entry in result.unmatched] == [(2, "EBICS-Server")]


def test_portfolio_weighs_services_by_criticality(seeded):
    result = assess_inventory(
        entries("Slack;;Chat;gering;nein", "Personio;;Personal;hoch;nein"), seeded, TODAY
    )

    by_slug = {service.slug: service for service in result.services}
    expected = (by_slug["slack"].assessment.score + 3 * by_slug["personio"].assessment.score) / 4
    assert result.portfolio.score == pytest.approx(expected)


def test_services_are_sorted_by_criticality_then_weakest_level(seeded):
    result = assess_inventory(
        entries(
            "Slack;;Chat;gering;nein",
            "Personio;;Personal;hoch;nein",
            "Okta;;Anmeldung;hoch;ja",
        ),
        seeded,
        TODAY,
    )

    assert [service.slug for service in result.services] == ["okta", "personio", "slack"]


def test_musterbank_is_assessed_completely(seeded):
    content = (DATA_DIR / "testdata" / "musterbank-it-bestand.xlsx").read_bytes()
    inventory = read_inventory(content, "musterbank.xlsx")

    result = assess_inventory(inventory.entries, seeded, TODAY)

    # Ohne KI. „SAP S/4“ bleibt offen, seit die Schreibweise „SAP“ entfernt ist (sie ordnete
    # „SAP Ariba“ still falsch zu). Ein Mensch oder die KI-Stufe ordnet ihn zu.
    assert len(result.services) == 46
    assert {entry.service for entry in result.unmatched} == {
        "EBICS-Server",
        "SAP S/4",
        "Bundesbank ExtraNet",
        "Outlook",
        "Microsoft Defender for Endpoint",
        "Treasury-Makros (Excel)",
    }
    assert result.portfolio.weakest_critical_level is not None
