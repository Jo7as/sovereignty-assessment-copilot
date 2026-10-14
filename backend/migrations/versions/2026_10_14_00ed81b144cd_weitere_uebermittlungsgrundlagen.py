"""weitere uebermittlungsgrundlagen

Revision ID: 00ed81b144cd
Revises: 0875236251fa
Create Date: 2026-10-14 14:23:59.266316

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00ed81b144cd"
down_revision: str | Sequence[str] | None = "0875236251fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD = (
    "transfer_basis IN ('NICHT_NOETIG', 'STANDARDVERTRAGSKLAUSELN', "
    "'DATA_PRIVACY_FRAMEWORK', 'KEINE', 'UNBEKANNT')"
)
NEW = (
    "transfer_basis IN ('NICHT_NOETIG', 'STANDARDVERTRAGSKLAUSELN', "
    "'DATA_PRIVACY_FRAMEWORK', 'ANGEMESSENHEITSBESCHLUSS', "
    "'VERBINDLICHE_UNTERNEHMENSREGELN', 'KEINE', 'UNBEKANNT')"
)
NAME = "ck_service_variant_transfer_basis"


def replace_check(condition: str) -> None:
    op.drop_constraint(op.f(NAME), "service_variant", type_="check")
    op.create_check_constraint(op.f(NAME), "service_variant", condition)


def upgrade() -> None:
    replace_check(NEW)


def downgrade() -> None:
    op.execute(
        "UPDATE service_variant SET transfer_basis = 'UNBEKANNT' WHERE transfer_basis IN "
        "('ANGEMESSENHEITSBESCHLUSS', 'VERBINDLICHE_UNTERNEHMENSREGELN')"
    )
    replace_check(OLD)
