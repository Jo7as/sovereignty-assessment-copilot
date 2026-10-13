from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    Category,
    Certificate,
    Country,
    Criticality,
    DataLocation,
    Dependency,
    DependencyKind,
    EuAlternative,
    Evidence,
    Jurisdiction,
    KeyManagement,
    MigrationEffort,
    OperationsLocation,
    Organization,
    RenewableEnergy,
    ReviewStatus,
    Service,
    ServiceAlias,
    ServiceVariant,
    VariantCertificate,
)


@pytest.fixture
def countries(session):
    countries = {
        "DE": Country(code="DE", name="Deutschland", jurisdiction=Jurisdiction.EU_EWR),
        "IE": Country(code="IE", name="Irland", jurisdiction=Jurisdiction.EU_EWR),
        "US": Country(code="US", name="USA", jurisdiction=Jurisdiction.USA),
    }
    session.add_all(countries.values())
    session.flush()
    return countries


@pytest.fixture
def microsoft(session, countries):
    parent = Organization(slug="microsoft", name="Microsoft Corporation", country_code="US")
    subsidiary = Organization(
        slug="microsoft-ireland",
        name="Microsoft Ireland Operations Ltd.",
        country_code="IE",
        ultimate_parent=parent,
    )
    session.add_all([parent, subsidiary])
    session.flush()
    return subsidiary


@pytest.fixture
def microsoft_365(session, microsoft):
    category = Category(slug="collaboration", name="Büro und Zusammenarbeit")
    service = Service(
        slug="microsoft-365",
        name="Microsoft 365",
        provider=microsoft,
        category=category,
        description="Büropaket mit E-Mail, Dokumenten und Videokonferenz",
        typical_criticality=Criticality.HOCH,
    )
    service.variants.append(ServiceVariant(slug="standard", name="Standard", is_default=True))
    session.add(service)
    session.flush()
    return service


def test_organization_slug_is_unique(session, microsoft):
    session.add(Organization(slug="microsoft", name="Doppelt", country_code="US"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_organization_cannot_be_its_own_parent(session, microsoft):
    microsoft.ultimate_parent_id = microsoft.id

    with pytest.raises(IntegrityError):
        session.flush()


def test_organization_requires_country(session):
    session.add(Organization(slug="ohne-land", name="Ohne Land"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_database_rejects_misspelled_enum_value(session):
    insert = text("INSERT INTO country (code, name, jurisdiction) VALUES ('XX', 'Test', 'EU_EWRR')")

    with pytest.raises(IntegrityError):
        session.execute(insert)


def test_new_variant_starts_as_unknown_and_unreviewed(session, microsoft_365):
    variant = microsoft_365.variants[0]

    assert variant.data_location is DataLocation.UNBEKANNT
    assert variant.key_management is KeyManagement.UNBEKANNT
    assert variant.renewable_energy is RenewableEnergy.KEINE_ANGABE
    assert variant.review_status is ReviewStatus.KI_VORSCHLAG


def test_service_has_at_most_one_default_variant(session, microsoft_365):
    microsoft_365.variants.append(ServiceVariant(slug="zweite", name="Zweite", is_default=True))

    with pytest.raises(IntegrityError):
        session.flush()


def test_variant_slug_is_unique_within_service(session, microsoft_365):
    microsoft_365.variants.append(ServiceVariant(slug="standard", name="Noch einmal"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_reviewed_variant_requires_review_date(session, microsoft_365):
    microsoft_365.variants[0].review_status = ReviewStatus.GEPRUEFT

    with pytest.raises(IntegrityError):
        session.flush()


def test_ai_verified_variant_requires_review_date(session, microsoft_365):
    microsoft_365.variants[0].review_status = ReviewStatus.KI_NACHGEPRUEFT

    with pytest.raises(IntegrityError):
        session.flush()


def test_ai_verified_variant_with_date_is_accepted(session, microsoft_365):
    variant = microsoft_365.variants[0]
    variant.review_status = ReviewStatus.KI_NACHGEPRUEFT
    variant.reviewed_at = date(2026, 10, 13)
    session.flush()
    session.expire_all()

    assert variant.review_status is ReviewStatus.KI_NACHGEPRUEFT


def test_alias_is_unique_regardless_of_case(session, microsoft_365):
    microsoft_365.aliases.append(ServiceAlias(alias="O365"))
    session.flush()
    microsoft_365.aliases.append(ServiceAlias(alias="o365"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_service_cannot_be_its_own_alternative(session, microsoft_365):
    session.add(
        EuAlternative(
            service=microsoft_365,
            alternative=microsoft_365,
            migration_effort=MigrationEffort.GERING,
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_evidence_requires_a_target(session):
    session.add(
        Evidence(
            attribute="data_location",
            source_url="https://example.com",
            retrieved_at=date(2026, 10, 13),
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_evidence_cannot_have_two_targets(session, microsoft, microsoft_365):
    session.add(
        Evidence(
            variant=microsoft_365.variants[0],
            organization=microsoft,
            attribute="data_location",
            source_url="https://example.com",
            retrieved_at=date(2026, 10, 13),
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_microsoft_365_example_round_trip(session, countries, microsoft, microsoft_365):
    """Das Beispiel aus docs/datenmodell.md: ein Dienst, drei Varianten."""
    sap = Organization(slug="sap", name="SAP SE", country_code="DE")
    delos = Organization(
        slug="delos-cloud", name="Delos Cloud GmbH", country_code="DE", ultimate_parent=sap
    )
    c5 = Certificate(slug="bsi-c5", name="BSI C5", issuer="BSI")

    boundary = ServiceVariant(
        slug="eu-data-boundary",
        name="EU Data Boundary",
        data_location=DataLocation.EU_ZUGESICHERT,
        operations_location=OperationsLocation.EU_MIT_AUSNAHMEN,
    )
    boundary.certificates.append(VariantCertificate(certificate=c5, valid_until=date(2027, 6, 30)))
    boundary.evidence.append(
        Evidence(
            attribute="data_location",
            source_url="https://example.com/eu-data-boundary",
            quote="Kundendaten werden in der EU gespeichert und verarbeitet.",
            retrieved_at=date(2026, 10, 13),
        )
    )

    delos_variant = ServiceVariant(
        slug="delos-cloud",
        name="Delos Cloud",
        operator=delos,
        data_location=DataLocation.EU_ZUGESICHERT,
        governing_law_country_code="DE",
        review_status=ReviewStatus.GEPRUEFT,
        reviewed_at=date(2026, 10, 13),
    )
    delos_variant.dependencies.append(
        Dependency(
            supplier=microsoft.ultimate_parent, kind=DependencyKind.TECHNOLOGIE, is_critical=True
        )
    )

    microsoft_365.variants.extend([boundary, delos_variant])
    microsoft_365.aliases.extend([ServiceAlias(alias="O365"), ServiceAlias(alias="Teams")])

    office_suite = Service(
        slug="eu-office",
        name="Europäisches Büropaket",
        provider=sap,
        category=microsoft_365.category,
        typical_criticality=Criticality.HOCH,
    )
    session.add(
        EuAlternative(
            service=microsoft_365,
            alternative=office_suite,
            migration_effort=MigrationEffort.HOCH,
            note="Deckt nur E-Mail und Kalender ab",
        )
    )
    session.flush()
    session.expire_all()

    loaded = session.scalars(select(Service).where(Service.slug == "microsoft-365")).one()
    variants = {variant.slug: variant for variant in loaded.variants}

    assert loaded.provider.country.jurisdiction is Jurisdiction.EU_EWR
    assert loaded.provider.ultimate_parent.country.jurisdiction is Jurisdiction.USA
    assert set(variants) == {"standard", "eu-data-boundary", "delos-cloud"}
    assert [variant.slug for variant in loaded.variants if variant.is_default] == ["standard"]
    assert {alias.alias for alias in loaded.aliases} == {"O365", "Teams"}

    assert variants["eu-data-boundary"].certificates[0].certificate.slug == "bsi-c5"
    assert variants["eu-data-boundary"].evidence[0].attribute == "data_location"

    assert variants["delos-cloud"].operator.country.jurisdiction is Jurisdiction.EU_EWR
    assert variants["delos-cloud"].governing_law_country.name == "Deutschland"
    dependency = variants["delos-cloud"].dependencies[0]
    assert dependency.supplier.slug == "microsoft"
    assert dependency.supplier.country.jurisdiction is Jurisdiction.USA

    assert loaded.alternatives[0].alternative.slug == "eu-office"
    assert loaded.alternatives[0].migration_effort is MigrationEffort.HOCH


def test_deleting_a_service_removes_its_variants(session, microsoft_365):
    session.delete(microsoft_365)
    session.flush()

    assert session.scalars(select(ServiceVariant)).all() == []
