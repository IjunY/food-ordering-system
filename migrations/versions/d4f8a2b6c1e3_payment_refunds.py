"""refunds: a paid order that is cancelled gets its money back

- payments.status can be REFUNDED (the column grows from 7 to 8 characters)
- payments.refunded_at: when the money was given back
- payments.refund_ref: the provider's refund id (LINE Pay refundTransactionId)

Revision ID: d4f8a2b6c1e3
Revises: b7e2a4c9d815
Create Date: 2026-11-23 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f8a2b6c1e3"
down_revision: str | Sequence[str] | None = "b7e2a4c9d815"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "payments",
        "status",
        existing_type=sa.String(length=7),
        type_=sa.String(length=8),
        existing_nullable=False,
    )
    op.add_column(
        "payments",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payments", sa.Column("refund_ref", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    refunded = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM payments WHERE status = 'REFUNDED'"))
        .scalar_one()
    )
    if refunded:
        raise RuntimeError(
            f"{refunded} payment(s) are REFUNDED, which the older schema cannot "
            "store. Keep this revision, or deal with those payments first."
        )
    op.drop_column("payments", "refund_ref")
    op.drop_column("payments", "refunded_at")
    op.alter_column(
        "payments",
        "status",
        existing_type=sa.String(length=8),
        type_=sa.String(length=7),
        existing_nullable=False,
    )
