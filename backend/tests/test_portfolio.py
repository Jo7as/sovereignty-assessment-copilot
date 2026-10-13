from dataclasses import replace
from datetime import date

import pytest

from app.models import Criticality, DataLocation, RenewableEnergy
from app.scoring import Objective, PortfolioItem, assess, assess_portfolio
from tests.test_scoring import sovereign, us_provider

TODAY = date(2026, 10, 13)


def item(name, criticality, facts) -> PortfolioItem:
    return PortfolioItem(name, criticality, assess(facts, TODAY))


def test_critical_services_weigh_three_times_as_much_as_minor_ones():
    portfolio = assess_portfolio(
        [
            item("Kernsystem", Criticality.HOCH, us_provider()),  # Stufe 1
            item("Umfragetool", Criticality.GERING, sovereign()),  # Stufe 4
        ]
    )

    # (3 x 1 + 1 x 4) / 4
    assert portfolio.level == 1.75
    assert portfolio.levels[Objective.STRATEGISCH] == 1.75


def test_medium_criticality_weighs_twice():
    portfolio = assess_portfolio(
        [
            item("A", Criticality.MITTEL, sovereign()),  # Wert 100
            item("B", Criticality.GERING, sovereign(renewable_energy=RenewableEnergy.ZUGESAGT)),
        ]
    )

    # (2 x 100 + 1 x 97.5) / 3
    assert portfolio.score == pytest.approx(99.1667, abs=0.001)


def test_portfolio_reports_secured_and_possible_values():
    unknown_location = sovereign(data_location=DataLocation.UNBEKANNT)

    portfolio = assess_portfolio([item("A", Criticality.HOCH, unknown_location)])

    assert (portfolio.level, portfolio.potential) == (0, 4)
    assert portfolio.score < portfolio.potential_score == 100
    assert portfolio.provisional_services == 1


def test_weakest_critical_service_is_reported():
    portfolio = assess_portfolio(
        [
            item("Kernsystem", Criticality.HOCH, sovereign()),
            item("Zweitsystem", Criticality.HOCH, us_provider()),
            item(
                "Umfragetool",
                Criticality.GERING,
                replace(us_provider(), data_location=DataLocation.NICHT_EU),
            ),
        ]
    )

    assert portfolio.weakest_critical_level == 1
    assert portfolio.weakest_critical_services == ("Zweitsystem",)


def test_portfolio_without_critical_services_has_no_weakest_critical_level():
    portfolio = assess_portfolio([item("A", Criticality.GERING, sovereign())])

    assert portfolio.weakest_critical_level is None
    assert portfolio.weakest_critical_services == ()


def test_distribution_counts_services_per_level():
    portfolio = assess_portfolio(
        [
            item("A", Criticality.HOCH, sovereign()),
            item("B", Criticality.MITTEL, us_provider()),
            item("C", Criticality.GERING, us_provider()),
        ]
    )

    assert portfolio.distribution == {0: 0, 1: 2, 2: 0, 3: 0, 4: 1}


def test_empty_portfolio_is_rejected():
    with pytest.raises(ValueError, match="mindestens einen Dienst"):
        assess_portfolio([])
