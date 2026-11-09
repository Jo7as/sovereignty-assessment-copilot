"""Verträge am Assessment (Tiefenprüfung)

Revision ID: e5c4892c26ba
Revises: 9fe24e87c8f7
Create Date: 2026-11-09 15:24:18.524585

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5c4892c26ba"
down_revision: str | Sequence[str] | None = "9fe24e87c8f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCUMENT_TYPES = (
    "AVV",
    "RAHMENVERTRAG",
    "LEISTUNGSBESCHREIBUNG",
    "STANDARDVERTRAGSKLAUSELN",
    "UNTERAUFTRAGNEHMER",
    "SONSTIGES",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "assessment_contract",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("pages", sa.JSON(), nullable=False),
        sa.Column("service_slug", sa.String(length=80), nullable=True),
        sa.Column(
            "document_type",
            sa.Enum(
                *DOCUMENT_TYPES,
                name="document_type",
                native_enum=False,
                create_constraint=False,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "document_type IN ({})".format(", ".join(f"'{value}'" for value in DOCUMENT_TYPES)),
            name=op.f("ck_assessment_contract_document_type"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessment.id"],
            name=op.f("fk_assessment_contract_assessment_id_assessment"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_contract")),
    )
    op.create_index(
        op.f("ix_assessment_contract_assessment_id"),
        "assessment_contract",
        ["assessment_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_assessment_contract_assessment_id"), table_name="assessment_contract")
    op.drop_table("assessment_contract")
