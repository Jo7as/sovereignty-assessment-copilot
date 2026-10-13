"""pruefstatus ki nachgeprueft

Revision ID: badbb5242e23
Revises: d3ebe22a18cc
Create Date: 2026-10-13 19:12:02.986293

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "badbb5242e23"
down_revision: str | Sequence[str] | None = "d3ebe22a18cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_VALUES = "review_status IN ('KI_VORSCHLAG', 'GEPRUEFT')"
NEW_VALUES = "review_status IN ('KI_VORSCHLAG', 'KI_NACHGEPRUEFT', 'GEPRUEFT')"
OLD_DATE_RULE = "review_status <> 'GEPRUEFT' OR reviewed_at IS NOT NULL"
NEW_DATE_RULE = "review_status = 'KI_VORSCHLAG' OR reviewed_at IS NOT NULL"

VALUES = op.f("ck_service_variant_review_status")
DATE_RULE = op.f("ck_service_variant_reviewed_has_date")


def replace_check(name: str, condition: str) -> None:
    op.drop_constraint(name, "service_variant", type_="check")
    op.create_check_constraint(name, "service_variant", condition)


def upgrade() -> None:
    replace_check(VALUES, NEW_VALUES)
    replace_check(DATE_RULE, NEW_DATE_RULE)


def downgrade() -> None:
    op.execute(
        "UPDATE service_variant SET review_status = 'KI_VORSCHLAG' "
        "WHERE review_status = 'KI_NACHGEPRUEFT'"
    )
    replace_check(DATE_RULE, OLD_DATE_RULE)
    replace_check(VALUES, OLD_VALUES)
