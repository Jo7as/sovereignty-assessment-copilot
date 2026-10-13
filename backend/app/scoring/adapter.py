"""Liest die Fakten einer Variante aus der Datenbank und bewertet sie."""

from datetime import date

from app.models import Jurisdiction, Organization, ServiceVariant
from app.scoring.assessment import assess
from app.scoring.model import CertificateFact, DependencyFact, ServiceAssessment, VariantFacts


def controlling_jurisdiction(organization: Organization) -> Jurisdiction:
    """Maßgeblich ist der Rechtsraum der obersten Konzernmutter, nicht der Sitz der Tochter."""
    return (organization.ultimate_parent or organization).country.jurisdiction


def facts_from_variant(variant: ServiceVariant) -> VariantFacts:
    operator = variant.operator
    law = variant.governing_law_country
    return VariantFacts(
        provider_jurisdiction=controlling_jurisdiction(variant.service.provider),
        operator_jurisdiction=controlling_jurisdiction(operator) if operator else None,
        operator_seat=operator.country.jurisdiction if operator else None,
        data_location=variant.data_location,
        operations_location=variant.operations_location,
        transfer_basis=variant.transfer_basis,
        governing_law=law.jurisdiction if law else None,
        key_management=variant.key_management,
        data_export=variant.data_export,
        openness=variant.openness,
        ai_training=variant.ai_training_on_customer_data,
        renewable_energy=variant.renewable_energy,
        certificates=tuple(
            CertificateFact(reference.certificate.slug, reference.valid_until)
            for reference in variant.certificates
        ),
        dependencies=tuple(
            DependencyFact(
                supplier=(dependency.supplier.ultimate_parent or dependency.supplier).name,
                jurisdiction=controlling_jurisdiction(dependency.supplier),
                kind=dependency.kind,
                critical=dependency.is_critical,
            )
            for dependency in variant.dependencies
        ),
        dependencies_complete=variant.dependencies_complete,
    )


def assess_variant(variant: ServiceVariant, today: date) -> ServiceAssessment:
    return assess(facts_from_variant(variant), today)
