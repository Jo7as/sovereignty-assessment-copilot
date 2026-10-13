"""Format der Seed-Dateien in data/, beschrieben in data/README.md."""

import datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.models.enums import (
    AiTraining,
    Criticality,
    DataExport,
    DataLocation,
    DependencyKind,
    Jurisdiction,
    KeyManagement,
    MigrationEffort,
    Openness,
    OperationsLocation,
    RenewableEnergy,
    ReviewStatus,
    TransferBasis,
)


class SeedModel(BaseModel):
    # Unbekannte Felder sind fast immer Tippfehler und werden abgelehnt
    model_config = ConfigDict(extra="forbid")


class Fact[T](SeedModel):
    """Eine Angabe, wahlweise mit Nachweis."""

    value: T
    source: str | None = None
    quote: str | None = None
    retrieved: datetime.date | None = None

    @model_validator(mode="after")
    def evidence_is_complete(self) -> Self:
        if (self.source is None) != (self.retrieved is None):
            raise ValueError("source und retrieved gehören zusammen")
        if self.quote is not None and self.source is None:
            raise ValueError("quote braucht eine source")
        return self


def _as_fact(value: Any) -> Any:
    """Erlaubt die Kurzform `feld: WERT` neben der Langform mit Nachweis."""
    return value if isinstance(value, dict) else {"value": value}


type Sourced[T] = Annotated[Fact[T], BeforeValidator(_as_fact)]


class CountrySeed(SeedModel):
    code: str = Field(pattern=r"^[A-Z]{2}$")
    name: str
    jurisdiction: Jurisdiction


class OrganizationSeed(SeedModel):
    slug: str
    name: str
    country: str
    parent: Sourced[str] | None = None


class CategorySeed(SeedModel):
    slug: str
    name: str


class CertificateSeed(SeedModel):
    slug: str
    name: str
    issuer: str | None = None


class CertificateRefSeed(SeedModel):
    certificate: str
    valid_until: datetime.date | None = None
    source: str
    quote: str | None = None
    retrieved: datetime.date


class DependencySeed(SeedModel):
    supplier: str
    kind: DependencyKind
    critical: bool = False
    source: str
    quote: str | None = None
    retrieved: datetime.date


class ReviewSeed(SeedModel):
    status: ReviewStatus
    date: datetime.date | None = None

    @model_validator(mode="after")
    def verified_has_date(self) -> Self:
        if self.status is not ReviewStatus.KI_VORSCHLAG and self.date is None:
            raise ValueError(f"{self.status} braucht ein Datum")
        return self


class VariantSeed(SeedModel):
    slug: str
    name: str
    default: bool = False
    operator: str | None = None
    data_location: Sourced[DataLocation] | None = None
    operations_location: Sourced[OperationsLocation] | None = None
    transfer_basis: Sourced[TransferBasis] | None = None
    governing_law: Sourced[str] | None = None
    key_management: Sourced[KeyManagement] | None = None
    data_export: Sourced[DataExport] | None = None
    openness: Sourced[Openness] | None = None
    ai_training_on_customer_data: Sourced[AiTraining] | None = None
    renewable_energy: Sourced[RenewableEnergy] | None = None
    certificates: list[CertificateRefSeed] = []
    dependencies: list[DependencySeed] = []
    review: ReviewSeed


class AlternativeSeed(SeedModel):
    service: str
    effort: MigrationEffort
    note: str | None = None


class ServiceSeed(SeedModel):
    slug: str
    name: str
    provider: str
    category: str
    description: str | None = None
    typical_criticality: Criticality
    aliases: list[str] = []
    variants: list[VariantSeed] = Field(min_length=1)
    alternatives: list[AlternativeSeed] = []
