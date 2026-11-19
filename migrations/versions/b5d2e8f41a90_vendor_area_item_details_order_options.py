"""vendor area and cover photo, item description and add-ons, order line add-ons

- vendors.area: which part of campus (fengyun / shuimu / snack / other)
- vendors.cover_image_url: banner photo at the top of the vendor's page
- menu_items.description_zh / description_en
- menu_items.option_groups: the item's add-on choices (JSON)
- order_items.options / note: the add-ons the customer picked and their note

Also joins the two migration branches (payments, and vendor/menu photos) back
into one, so `alembic upgrade head` has a single head to go to.

Existing rows get the defaults (area "other", no cover, empty description, no
add-ons); running scripts/seed_demo.py again fills them in for the NTHU vendors.

Revision ID: b5d2e8f41a90
Revises: 1c11d8b50145, 79476f52b809
Create Date: 2026-11-19 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5d2e8f41a90"
down_revision: str | Sequence[str] | None = ("1c11d8b50145", "79476f52b809")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "vendors",
        sa.Column("area", sa.String(length=20), server_default="other", nullable=False),
    )
    op.add_column(
        "vendors", sa.Column("cover_image_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "menu_items",
        sa.Column("description_zh", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "menu_items",
        sa.Column("description_en", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "menu_items",
        sa.Column(
            "option_groups", sa.JSON(), server_default=sa.text("'[]'"), nullable=False
        ),
    )
    op.add_column(
        "order_items",
        sa.Column("options", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "order_items",
        sa.Column("note", sa.String(length=60), server_default="", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order_items", "note")
    op.drop_column("order_items", "options")
    op.drop_column("menu_items", "option_groups")
    op.drop_column("menu_items", "description_en")
    op.drop_column("menu_items", "description_zh")
    op.drop_column("vendors", "cover_image_url")
    op.drop_column("vendors", "area")
