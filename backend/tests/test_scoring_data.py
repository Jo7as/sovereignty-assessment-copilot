"""Bewertung der echten Anbieterdaten: prüft das Zusammenspiel von Daten und Regeln."""

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Service, ServiceVariant
from app.scoring import Objective, assess_variant
from app.seed import load_seed

REAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TODAY = date(2026, 10, 13)


@pytest.fixture
def assessed(session):
    load_seed(session, REAL_DATA_DIR)

    def assess_by_slug(service: str, variant: str = "standard"):
        row = session.scalars(
            select(ServiceVariant)
            .join(Service)
            .where(Service.slug == service, ServiceVariant.slug == variant)
        ).one()
        return assess_variant(row, TODAY)

    return assess_by_slug


def test_us_provider_without_eu_operating_company(assessed):
    result = assessed("microsoft-365")

    assert result.objectives[Objective.STRATEGISCH].level == 1
    assert result.potential == 1


def test_eu_operating_company_under_us_control(assessed):
    result = assessed("amazon-web-services", "european-sovereign-cloud")

    assert result.objectives[Objective.STRATEGISCH].level == 2
    assert result.potential == 2


def test_eu_operator_on_us_technology(assessed):
    result = assessed("microsoft-365", "delos-cloud")

    assert result.objectives[Objective.STRATEGISCH].level == 3
    assert result.objectives[Objective.LIEFERKETTE].level == 2
    assert result.potential == 2


def test_eu_provider_hosted_by_us_cloud(assessed):
    result = assessed("personio")

    supply_chain = result.objectives[Objective.LIEFERKETTE]
    assert (supply_chain.level, supply_chain.potential) == (2, 2)
    assert "Amazon" in supply_chain.limiting[0].reason


def test_eu_provider_with_unreviewed_supply_chain(assessed):
    result = assessed("stackit")

    supply_chain = result.objectives[Objective.LIEFERKETTE]
    assert (supply_chain.level, supply_chain.potential) == (2, 4)
    assert "dependencies" in result.gaps


def test_known_non_critical_dependency_caps_the_possible_level(assessed):
    result = assessed("datev")

    supply_chain = result.objectives[Objective.LIEFERKETTE]
    assert (supply_chain.level, supply_chain.potential) == (2, 3)
    assert "Microsoft" in supply_chain.findings[1].reason


def test_entry_without_facts_is_rated_lowest_and_marked_provisional(assessed):
    result = assessed("servicenow")

    assert result.level == 0
    assert result.is_provisional


def test_every_variant_can_be_assessed(session):
    load_seed(session, REAL_DATA_DIR)

    for variant in session.scalars(select(ServiceVariant)):
        result = assess_variant(variant, TODAY)
        assert 0 <= result.level <= result.potential <= 4
