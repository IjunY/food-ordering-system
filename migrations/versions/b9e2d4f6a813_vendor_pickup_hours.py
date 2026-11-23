"""vendors choose whether and when customers can book a pickup time

Revision ID: b9e2d4f6a813
Revises: a8d3f5c2e7b1
Create Date: 2026-11-23 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9e2d4f6a813"
down_revision: str | Sequence[str] | None = "a8d3f5c2e7b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing vendors keep taking bookings at any time, as before
    op.add_column(
        "vendors",
        sa.Column(
            "allow_scheduled_pickup",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "vendors",
        sa.Column(
            "pickup_hours", sa.JSON(), server_default=sa.text("'[]'"), nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("vendors", "pickup_hours")
    op.drop_column("vendors", "allow_scheduled_pickup")
