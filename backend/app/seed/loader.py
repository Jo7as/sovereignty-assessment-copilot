"""Überträgt die Seed-Dateien aus data/ in die Datenbank.

Die Dateien sind die Quelle der Wahrheit: Nach dem Laden entspricht die Datenbank genau
ihrem Stand. Bei einem Fehler in den Dateien wird nichts geschrieben.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    AiTraining,
    Category,
    Certificate,
    Country,
    DataExport,
    DataLocation,
    Dependency,
    EuAlternative,
    Evidence,
    KeyManagement,
    Openness,
    OperationsLocation,
    Organization,
    RenewableEnergy,
    Service,
    ServiceAlias,
    ServiceVariant,
    TransferBasis,
    VariantCertificate,
)
from app.seed.schema import (
    CategorySeed,
    CertificateSeed,
    CountrySeed,
    Fact,
    OrganizationSeed,
    ServiceSeed,
    VariantSeed,
)

# Merkmale einer Variante und der Wert, der gilt, wenn die Datei nichts nennt
VARIANT_FACTS = {
    "data_location": DataLocation.UNBEKANNT,
    "operations_location": OperationsLocation.UNBEKANNT,
    "transfer_basis": TransferBasis.UNBEKANNT,
    "key_management": KeyManagement.UNBEKANNT,
    "data_export": DataExport.UNBEKANNT,
    "openness": Openness.UNBEKANNT,
    "ai_training_on_customer_data": AiTraining.UNBEKANNT,
    "renewable_energy": RenewableEnergy.KEINE_ANGABE,
}

# Diese Merkmale bestimmen die Stufe und brauchen deshalb einen Nachweis
EVIDENCE_REQUIRED = ("data_location", "key_management")


class SeedError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass
class SeedData:
    countries: list[CountrySeed] = field(default_factory=list)
    organizations: list[OrganizationSeed] = field(default_factory=list)
    categories: list[CategorySeed] = field(default_factory=list)
    certificates: list[CertificateSeed] = field(default_factory=list)
    services: dict[str, ServiceSeed] = field(default_factory=dict)  # Dateiname -> Dienst


@dataclass
class SeedReport:
    countries: int
    organizations: int
    categories: int
    certificates: int
    services: int
    variants: int
    evidence: int


def load_seed(session: Session, data_dir: Path) -> SeedReport:
    """Prüft die Dateien und gleicht die Datenbank an. Der Aufrufer bestätigt die Transaktion."""
    data, errors = read_seed(data_dir)
    errors += check_rules(data)
    if errors:
        raise SeedError(errors)
    return write_seed(session, data)


def read_seed(data_dir: Path) -> tuple[SeedData, list[str]]:
    data = SeedData()
    errors: list[str] = []

    def parse(file: Path, schema: type) -> object | None:
        name = file.relative_to(data_dir).as_posix()
        try:
            content = yaml.safe_load(file.read_text(encoding="utf-8"))
            return TypeAdapter(schema).validate_python(content)
        except FileNotFoundError:
            errors.append(f"{name}: Datei fehlt")
        except yaml.YAMLError as error:
            errors.append(f"{name}: kein gültiges YAML ({error})")
        except ValidationError as error:
            for issue in error.errors():
                location = ".".join(str(part) for part in issue["loc"])
                errors.append(f"{name}: {location}: {issue['msg']}")
        return None

    data.countries = parse(data_dir / "countries.yaml", list[CountrySeed]) or []
    data.organizations = parse(data_dir / "organizations.yaml", list[OrganizationSeed]) or []
    data.categories = parse(data_dir / "categories.yaml", list[CategorySeed]) or []
    data.certificates = parse(data_dir / "certificates.yaml", list[CertificateSeed]) or []
    for file in sorted((data_dir / "services").glob("*.yaml")):
        if file.name.startswith("_"):
            continue
        service = parse(file, ServiceSeed)
        if service is not None:
            data.services[file.relative_to(data_dir).as_posix()] = service

    return data, errors


def check_rules(data: SeedData) -> list[str]:
    """Regeln, die über einzelne Felder hinausgehen. Siehe data/README.md."""
    errors: list[str] = []
    countries = {country.code for country in data.countries}
    organizations = {organization.slug for organization in data.organizations}
    categories = {category.slug for category in data.categories}
    certificates = {certificate.slug for certificate in data.certificates}
    services = {service.slug for service in data.services.values()}

    def check_reference(where: str, kind: str, value: str | None, known: set[str]) -> None:
        if value is not None and value not in known:
            errors.append(f"{where}: {kind} „{value}“ ist nicht angelegt")

    def check_unique(file: str, slugs: list[str]) -> None:
        for slug, occurrences in Counter(slugs).items():
            if occurrences > 1:
                errors.append(f"{file}: „{slug}“ kommt mehrfach vor")

    check_unique("countries.yaml", [country.code for country in data.countries])
    check_unique("organizations.yaml", [organization.slug for organization in data.organizations])
    check_unique("categories.yaml", [category.slug for category in data.categories])
    check_unique("certificates.yaml", [certificate.slug for certificate in data.certificates])

    for organization in data.organizations:
        where = f"organizations.yaml: {organization.slug}"
        check_reference(where, "Land", organization.country, countries)
        if organization.parent is not None:
            check_reference(where, "Konzernmutter", organization.parent.value, organizations)
            if organization.parent.value == organization.slug:
                errors.append(
                    f"{where}: ein Unternehmen kann nicht seine eigene Konzernmutter sein"
                )
            if organization.parent.source is None:
                errors.append(f"{where}: parent braucht einen Nachweis (source und retrieved)")

    aliases: dict[str, str] = {}
    for file, service in data.services.items():
        if file != f"services/{service.slug}.yaml":
            errors.append(f"{file}: Dateiname und slug „{service.slug}“ passen nicht zusammen")
        check_reference(file, "Anbieter", service.provider, organizations)
        check_reference(file, "Kategorie", service.category, categories)

        for alias in service.aliases:
            other = aliases.setdefault(alias.lower(), file)
            if other != file or service.aliases.count(alias) > 1:
                errors.append(f"{file}: Schreibweise „{alias}“ ist schon vergeben ({other})")

        defaults = sum(variant.default for variant in service.variants)
        if defaults != 1:
            errors.append(f"{file}: genau eine Standardvariante nötig, gefunden: {defaults}")
        check_unique(file, [variant.slug for variant in service.variants])

        for variant in service.variants:
            where = f"{file}: variants[{variant.slug}]"
            check_reference(where, "Betreiber", variant.operator, organizations)
            if variant.governing_law is not None:
                check_reference(where, "Land", variant.governing_law.value, countries)
            for name in EVIDENCE_REQUIRED:
                fact = getattr(variant, name)
                if fact is not None and fact.source is None:
                    errors.append(f"{where}.{name}: braucht einen Nachweis (source und retrieved)")
            for reference in variant.certificates:
                check_reference(where, "Zertifikat", reference.certificate, certificates)
            for dependency in variant.dependencies:
                check_reference(where, "Zulieferer", dependency.supplier, organizations)

        for alternative in service.alternatives:
            check_reference(file, "Alternative", alternative.service, services)
            if alternative.service == service.slug:
                errors.append(f"{file}: ein Dienst kann nicht seine eigene Alternative sein")

    return errors


def write_seed(session: Session, data: SeedData) -> SeedReport:
    # Abhängige Zeilen haben keine Verweise von außen und werden neu aufgebaut.
    # Länder, Unternehmen, Dienste und Varianten behalten ihre Nummern.
    for model in (Evidence, VariantCertificate, Dependency, EuAlternative, ServiceAlias):
        session.execute(delete(model))

    def existing(model: type, key: str) -> dict:
        return {getattr(row, key): row for row in session.scalars(select(model))}

    def upsert(known: dict, model: type, key: str, value: str):
        row = known.pop(value, None)
        if row is None:
            row = model(**{key: value})
            session.add(row)
        return row

    old_countries = existing(Country, "code")
    for seed in data.countries:
        country = upsert(old_countries, Country, "code", seed.code)
        country.name, country.jurisdiction = seed.name, seed.jurisdiction

    old_categories = existing(Category, "slug")
    categories = {}
    for seed in data.categories:
        categories[seed.slug] = category = upsert(old_categories, Category, "slug", seed.slug)
        category.name = seed.name

    old_certificates = existing(Certificate, "slug")
    certificates = {}
    for seed in data.certificates:
        certificates[seed.slug] = certificate = upsert(
            old_certificates, Certificate, "slug", seed.slug
        )
        certificate.name, certificate.issuer = seed.name, seed.issuer

    old_organizations = existing(Organization, "slug")
    organizations = {}
    for seed in data.organizations:
        organizations[seed.slug] = organization = upsert(
            old_organizations, Organization, "slug", seed.slug
        )
        organization.name, organization.country_code = seed.name, seed.country
    for seed in data.organizations:
        organization = organizations[seed.slug]
        organization.ultimate_parent = organizations[seed.parent.value] if seed.parent else None
        if seed.parent is not None:
            session.add(_evidence("ultimate_parent", seed.parent, organization=organization))

    old_services = existing(Service, "slug")
    services = {}
    for seed in data.services.values():
        services[seed.slug] = service = upsert(old_services, Service, "slug", seed.slug)
        service.name, service.description = seed.name, seed.description
        service.provider = organizations[seed.provider]
        service.category = categories[seed.category]
        service.typical_criticality = seed.typical_criticality
        service.aliases = [ServiceAlias(alias=alias) for alias in seed.aliases]

        old_variants = {variant.slug: variant for variant in service.variants}
        for variant_seed in seed.variants:
            variant = old_variants.pop(variant_seed.slug, None)
            if variant is None:
                variant = ServiceVariant(slug=variant_seed.slug)
                service.variants.append(variant)
            _fill_variant(variant, variant_seed, organizations, certificates)
        for removed in old_variants.values():
            service.variants.remove(removed)

    for seed in data.services.values():
        services[seed.slug].alternatives = [
            EuAlternative(
                alternative=services[alternative.service],
                migration_effort=alternative.effort,
                note=alternative.note,
            )
            for alternative in seed.alternatives
        ]

    # Was nicht mehr in den Dateien steht, wird entfernt. Dienste zuerst, weil sie auf
    # Unternehmen und Kategorien verweisen.
    for leftovers in (old_services, old_organizations, old_categories, old_certificates):
        for row in leftovers.values():
            session.delete(row)
        session.flush()
    for row in old_countries.values():
        session.delete(row)
    session.flush()

    return SeedReport(
        countries=len(data.countries),
        organizations=len(data.organizations),
        categories=len(data.categories),
        certificates=len(data.certificates),
        services=len(data.services),
        variants=sum(len(service.variants) for service in data.services.values()),
        evidence=len(session.scalars(select(Evidence.id)).all()),
    )


def _fill_variant(
    variant: ServiceVariant,
    seed: VariantSeed,
    organizations: dict[str, Organization],
    certificates: dict[str, Certificate],
) -> None:
    variant.name, variant.is_default = seed.name, seed.default
    variant.operator = organizations[seed.operator] if seed.operator else None
    variant.governing_law_country_code = seed.governing_law.value if seed.governing_law else None
    variant.review_status, variant.reviewed_at = seed.review.status, seed.review.date
    variant.dependencies_complete = seed.dependencies_complete

    evidence = []
    for name, unknown in VARIANT_FACTS.items():
        fact = getattr(seed, name)
        setattr(variant, name, fact.value if fact else unknown)
        if fact is not None and fact.source is not None:
            evidence.append(_evidence(name, fact))
    if seed.governing_law is not None and seed.governing_law.source is not None:
        evidence.append(_evidence("governing_law", seed.governing_law))

    variant.certificates = [
        VariantCertificate(
            certificate=certificates[reference.certificate], valid_until=reference.valid_until
        )
        for reference in seed.certificates
    ]
    evidence += [
        _evidence(f"certificate:{reference.certificate}", reference)
        for reference in seed.certificates
    ]

    variant.dependencies = [
        Dependency(
            supplier=organizations[dependency.supplier],
            kind=dependency.kind,
            is_critical=dependency.critical,
        )
        for dependency in seed.dependencies
    ]
    evidence += [
        _evidence(f"dependency:{dependency.supplier}:{dependency.kind}", dependency)
        for dependency in seed.dependencies
    ]

    variant.evidence = evidence


def _evidence(attribute: str, source: Fact, **target: object) -> Evidence:
    """`source` ist jede Angabe mit den Feldern source, quote und retrieved."""
    return Evidence(
        attribute=attribute,
        source_url=source.source,
        quote=source.quote,
        retrieved_at=source.retrieved,
        **target,
    )
