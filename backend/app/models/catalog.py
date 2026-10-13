"""Tabellen der Anbieterdatenbank, erklärt in docs/datenmodell.md."""

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type
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


class Country(TimestampMixin, Base):
    __tablename__ = "country"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    jurisdiction: Mapped[Jurisdiction] = mapped_column(enum_type(Jurisdiction, "jurisdiction"))


class Organization(TimestampMixin, Base):
    __tablename__ = "organization"
    __table_args__ = (CheckConstraint("ultimate_parent_id <> id", name="not_own_parent"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(ForeignKey("country.code"))
    ultimate_parent_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))

    country: Mapped[Country] = relationship()
    ultimate_parent: Mapped["Organization | None"] = relationship(remote_side=[id])


class Category(TimestampMixin, Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))


class Service(TimestampMixin, Base):
    __tablename__ = "service"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    provider_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    description: Mapped[str | None] = mapped_column(Text)
    typical_criticality: Mapped[Criticality] = mapped_column(
        enum_type(Criticality, "typical_criticality")
    )

    provider: Mapped[Organization] = relationship()
    category: Mapped[Category] = relationship()
    aliases: Mapped[list["ServiceAlias"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    variants: Mapped[list["ServiceVariant"]] = relationship(
        back_populates="service", cascade="all, delete-orphan", order_by="ServiceVariant.id"
    )
    alternatives: Mapped[list["EuAlternative"]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
        foreign_keys="EuAlternative.service_id",
    )


class ServiceAlias(TimestampMixin, Base):
    __tablename__ = "service_alias"
    __table_args__ = (Index("uq_service_alias_alias_lower", text("lower(alias)"), unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(200))

    service: Mapped[Service] = relationship(back_populates="aliases")


class ServiceVariant(TimestampMixin, Base):
    __tablename__ = "service_variant"
    __table_args__ = (
        UniqueConstraint("service_id", "slug"),
        Index(
            "uq_service_variant_one_default",
            "service_id",
            unique=True,
            postgresql_where="is_default",
        ),
        CheckConstraint(
            "review_status = 'KI_VORSCHLAG' OR reviewed_at IS NOT NULL",
            name="reviewed_has_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    is_default: Mapped[bool] = mapped_column(default=False)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))

    data_location: Mapped[DataLocation] = mapped_column(
        enum_type(DataLocation, "data_location"), default=DataLocation.UNBEKANNT
    )
    operations_location: Mapped[OperationsLocation] = mapped_column(
        enum_type(OperationsLocation, "operations_location"), default=OperationsLocation.UNBEKANNT
    )
    transfer_basis: Mapped[TransferBasis] = mapped_column(
        enum_type(TransferBasis, "transfer_basis"), default=TransferBasis.UNBEKANNT
    )
    governing_law_country_code: Mapped[str | None] = mapped_column(ForeignKey("country.code"))
    key_management: Mapped[KeyManagement] = mapped_column(
        enum_type(KeyManagement, "key_management"), default=KeyManagement.UNBEKANNT
    )
    data_export: Mapped[DataExport] = mapped_column(
        enum_type(DataExport, "data_export"), default=DataExport.UNBEKANNT
    )
    openness: Mapped[Openness] = mapped_column(
        enum_type(Openness, "openness"), default=Openness.UNBEKANNT
    )
    ai_training_on_customer_data: Mapped[AiTraining] = mapped_column(
        enum_type(AiTraining, "ai_training_on_customer_data"), default=AiTraining.UNBEKANNT
    )
    renewable_energy: Mapped[RenewableEnergy] = mapped_column(
        enum_type(RenewableEnergy, "renewable_energy"), default=RenewableEnergy.KEINE_ANGABE
    )

    # Sind die Zulieferer vollständig geprüft? Ohne Prüfung lässt sich eine Abhängigkeit
    # außerhalb der EU nicht ausschließen.
    dependencies_complete: Mapped[bool] = mapped_column(default=False, server_default=false())

    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "review_status"), default=ReviewStatus.KI_VORSCHLAG
    )
    reviewed_at: Mapped[date | None]

    service: Mapped[Service] = relationship(back_populates="variants")
    operator: Mapped[Organization | None] = relationship()
    governing_law_country: Mapped[Country | None] = relationship()
    certificates: Mapped[list["VariantCertificate"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["Dependency"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )


class Certificate(TimestampMixin, Base):
    __tablename__ = "certificate"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str | None] = mapped_column(String(200))


class VariantCertificate(TimestampMixin, Base):
    __tablename__ = "variant_certificate"
    __table_args__ = (UniqueConstraint("variant_id", "certificate_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("service_variant.id", ondelete="CASCADE"))
    certificate_id: Mapped[int] = mapped_column(ForeignKey("certificate.id"))
    valid_until: Mapped[date | None]

    variant: Mapped[ServiceVariant] = relationship(back_populates="certificates")
    certificate: Mapped[Certificate] = relationship()


class Dependency(TimestampMixin, Base):
    __tablename__ = "dependency"
    __table_args__ = (UniqueConstraint("variant_id", "supplier_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("service_variant.id", ondelete="CASCADE"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))
    kind: Mapped[DependencyKind] = mapped_column(enum_type(DependencyKind, "kind"))
    is_critical: Mapped[bool] = mapped_column(default=False)

    variant: Mapped[ServiceVariant] = relationship(back_populates="dependencies")
    supplier: Mapped[Organization] = relationship()


class EuAlternative(TimestampMixin, Base):
    __tablename__ = "eu_alternative"
    __table_args__ = (
        UniqueConstraint("service_id", "alternative_service_id"),
        CheckConstraint("service_id <> alternative_service_id", name="not_own_alternative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"))
    alternative_service_id: Mapped[int] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE")
    )
    migration_effort: Mapped[MigrationEffort] = mapped_column(
        enum_type(MigrationEffort, "migration_effort")
    )
    note: Mapped[str | None] = mapped_column(Text)

    service: Mapped[Service] = relationship(
        back_populates="alternatives", foreign_keys=[service_id]
    )
    alternative: Mapped[Service] = relationship(foreign_keys=[alternative_service_id])


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "(variant_id IS NULL) <> (organization_id IS NULL)", name="exactly_one_target"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_variant.id", ondelete="CASCADE")
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE")
    )
    attribute: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(Text)
    quote: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[date]

    variant: Mapped[ServiceVariant | None] = relationship(back_populates="evidence")
    organization: Mapped[Organization | None] = relationship()
