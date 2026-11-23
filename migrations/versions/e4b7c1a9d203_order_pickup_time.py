"""orders can book a pickup time (scheduled pickup)

Revision ID: e4b7c1a9d203
Revises: 630baecd2949
Create Date: 2026-11-23 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4b7c1a9d203"
down_revision: str | Sequence[str] | None = "630baecd2949"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing orders keep NULL = "as soon as possible"
    op.add_column(
        "orders",
        sa.Column("pickup_time", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "pickup_time")
