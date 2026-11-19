"""payment checkout address and provider transaction id; pay at pickup on orders

- payments.checkout_url: the provider's payment page, reused when the customer
  presses "pay" again (LINE Pay cannot start the same order id twice)
- payments.provider_ref: the provider's own transaction id (LINE Pay
  transactionId), checked when the customer comes back to confirm
- orders.pay_at_pickup: the customer will pay at the counter instead of online

Revision ID: c3a7f9d2e614
Revises: b5d2e8f41a90
Create Date: 2026-11-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a7f9d2e614"
down_revision: str | Sequence[str] | None = "b5d2e8f41a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "payments", sa.Column("checkout_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "payments", sa.Column("provider_ref", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "orders",
        sa.Column(
            "pay_at_pickup", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "pay_at_pickup")
    op.drop_column("payments", "provider_ref")
    op.drop_column("payments", "checkout_url")
