"""Vertragsanalyse: Läufe, Angaben und Einordnungsvorschlag

Revision ID: b7d1a3f0c2e4
Revises: e5c4892c26ba
Create Date: 2026-11-10 10:12:31.204118

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d1a3f0c2e4"
down_revision: str | Sequence[str] | None = "e5c4892c26ba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUSES = ("LAEUFT", "FERTIG", "FEHLER")
FINDING_STATUSES = ("KI_VORSCHLAG", "GEPRUEFT", "VERWORFEN")


def enum_column(enum_name: str, values: tuple[str, ...]) -> sa.Column:
    return sa.Column(
        "status",
        sa.Enum(*values, name=enum_name, native_enum=False, create_constraint=False, length=40),
        nullable=False,
    )


def enum_check(table: str, enum_name: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "status IN ({})".format(", ".join(f"'{value}'" for value in values)),
        name=op.f(f"ck_{table}_{enum_name}"),
    )


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            name,
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        )
        for name in ("created_at", "updated_at")
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("assessment_contract", sa.Column("classification", sa.JSON(), nullable=True))
    op.create_table(
        "contract_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        enum_column("run_status", RUN_STATUSES),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("log", sa.JSON(), nullable=False),
        *timestamps(),
        enum_check("contract_run", "run_status", RUN_STATUSES),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["assessment_contract.id"],
            name=op.f("fk_contract_run_contract_id_assessment_contract"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contract_run")),
    )
    op.create_index(
        op.f("ix_contract_run_contract_id"), "contract_run", ["contract_id"], unique=False
    )
    op.create_table(
        "contract_finding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=60), nullable=False),
        sa.Column("value", sa.String(length=60), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        enum_column("finding_status", FINDING_STATUSES),
        *timestamps(),
        enum_check("contract_finding", "finding_status", FINDING_STATUSES),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["contract_run.id"],
            name=op.f("fk_contract_finding_run_id_contract_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contract_finding")),
    )
    op.create_index(
        op.f("ix_contract_finding_run_id"), "contract_finding", ["run_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_contract_finding_run_id"), table_name="contract_finding")
    op.drop_table("contract_finding")
    op.drop_index(op.f("ix_contract_run_contract_id"), table_name="contract_run")
    op.drop_table("contract_run")
    op.drop_column("assessment_contract", "classification")
