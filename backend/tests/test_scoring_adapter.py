"""Ableitung der Fakten aus den Datenbankobjekten, ohne Datenbank."""

from app.models import Country, Jurisdiction, Organization
from app.scoring.adapter import controlling_jurisdiction

GERMANY = Country(code="DE", name="Deutschland", jurisdiction=Jurisdiction.EU_EWR)
IRELAND = Country(code="IE", name="Irland", jurisdiction=Jurisdiction.EU_EWR)
USA = Country(code="US", name="USA", jurisdiction=Jurisdiction.USA)
SWITZERLAND = Country(code="CH", name="Schweiz", jurisdiction=Jurisdiction.ANGEMESSEN)


def organization(country: Country, parent: Organization | None = None) -> Organization:
    return Organization(slug="x", name="X", country=country, ultimate_parent=parent)


def test_eu_subsidiary_of_us_parent_is_controlled_from_the_us():
    assert controlling_jurisdiction(organization(IRELAND, organization(USA))) is Jurisdiction.USA


def test_us_subsidiary_of_eu_parent_is_still_exposed_to_us_law():
    """Beispiel SAP Concur: US-Gesellschaft, Konzernmutter in Deutschland."""
    assert controlling_jurisdiction(organization(USA, organization(GERMANY))) is Jurisdiction.USA


def test_swiss_subsidiary_of_eu_parent_counts_as_adequate_country():
    result = controlling_jurisdiction(organization(SWITZERLAND, organization(GERMANY)))

    assert result is Jurisdiction.ANGEMESSEN


def test_independent_company_counts_with_its_own_seat():
    assert controlling_jurisdiction(organization(GERMANY)) is Jurisdiction.EU_EWR
