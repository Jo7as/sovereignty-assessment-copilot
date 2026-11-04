"""datenstandort eu und angemessen

Revision ID: 9fe24e87c8f7
Revises: d45707cfd018
Create Date: 2026-11-04 11:54:43.817736

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9fe24e87c8f7"
down_revision: str | Sequence[str] | None = "d45707cfd018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD = "data_location IN ('EU_ZUGESICHERT', 'EU_WAEHLBAR', 'NICHT_EU', 'UNBEKANNT')"
NEW = (
    "data_location IN ('EU_ZUGESICHERT', 'EU_WAEHLBAR', 'EU_UND_ANGEMESSEN', "
    "'NICHT_EU', 'UNBEKANNT')"
)
NAME = "ck_service_variant_data_location"


def replace_check(condition: str) -> None:
    op.drop_constraint(op.f(NAME), "service_variant", type_="check")
    op.create_check_constraint(op.f(NAME), "service_variant", condition)


def upgrade() -> None:
    replace_check(NEW)


def downgrade() -> None:
    op.execute(
        "UPDATE service_variant SET data_location = 'UNBEKANNT' "
        "WHERE data_location = 'EU_UND_ANGEMESSEN'"
    )
    replace_check(OLD)
