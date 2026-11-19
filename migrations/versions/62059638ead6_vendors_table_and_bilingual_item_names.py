"""vendors table and bilingual item names

Works on a database that already has menu items and orders: new columns are
added as nullable, filled in from the old data, and only then made NOT NULL.

Revision ID: 62059638ead6
Revises: 98a9c9588462
Create Date: 2026-11-17 15:48:29.643002

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "62059638ead6"
down_revision: str | Sequence[str] | None = "98a9c9588462"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_zh", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("description_zh", sa.Text(), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("opening_hours_zh", sa.String(length=100), nullable=False),
        sa.Column("opening_hours_en", sa.String(length=100), nullable=False),
        sa.Column("location_zh", sa.String(length=100), nullable=False),
        sa.Column("location_en", sa.String(length=100), nullable=False),
        sa.Column(
            "is_accepting_orders",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vendors")),
    )

    # 1. One vendor per distinct old menu_items.vendor string. The old data has
    #    no English name or details, so the Chinese name is reused and the rest
    #    is left empty for the vendor to fill in later.
    op.execute(
        """
        INSERT INTO vendors (name_zh, name_en, description_zh, description_en,
                             opening_hours_zh, opening_hours_en,
                             location_zh, location_en)
        SELECT DISTINCT vendor, vendor, '', '', '', '', '', ''
        FROM menu_items
        ORDER BY vendor
        """
    )

    # 2. New menu_items columns: nullable first, backfilled, then NOT NULL
    op.add_column("menu_items", sa.Column("vendor_id", sa.Integer(), nullable=True))
    for column in ("item_name_zh", "item_name_en", "category_zh", "category_en"):
        op.add_column(
            "menu_items", sa.Column(column, sa.String(length=100), nullable=True)
        )
    op.add_column("menu_items", sa.Column("prep_minutes", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE menu_items AS m
        SET vendor_id = v.id,
            item_name_zh = m.item_name,
            item_name_en = m.item_name,
            category_zh = '其他',
            category_en = 'Other',
            prep_minutes = 0
        FROM vendors AS v
        WHERE v.name_zh = m.vendor
        """
    )
    for column in (
        "vendor_id",
        "item_name_zh",
        "item_name_en",
        "category_zh",
        "category_en",
        "prep_minutes",
    ):
        op.alter_column("menu_items", column, nullable=False)
    op.create_foreign_key(
        op.f("fk_menu_items_vendor_id_vendors"),
        "menu_items",
        "vendors",
        ["vendor_id"],
        ["id"],
    )
    op.drop_column("menu_items", "item_name")
    op.drop_column("menu_items", "vendor")

    # 3. orders.vendor_id comes from the order's items (an order's items all
    #    came from one vendor in practice; MIN() just picks one if not).
    op.add_column("orders", sa.Column("vendor_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE orders AS o
        SET vendor_id = sub.vendor_id
        FROM (
            SELECT oi.order_id, MIN(m.vendor_id) AS vendor_id
            FROM order_items AS oi
            JOIN menu_items AS m ON m.id = oi.item_id
            GROUP BY oi.order_id
        ) AS sub
        WHERE sub.order_id = o.id
        """
    )
    # Orders without any items have no vendor to point at; they get a
    # placeholder vendor so no order is lost.
    op.execute(
        """
        INSERT INTO vendors (name_zh, name_en, description_zh, description_en,
                             opening_hours_zh, opening_hours_en,
                             location_zh, location_en, is_accepting_orders)
        SELECT '（舊資料）未知店家', '(old data) Unknown vendor', '', '', '', '',
               '', '', false
        WHERE EXISTS (SELECT 1 FROM orders WHERE vendor_id IS NULL)
        """
    )
    op.execute(
        """
        UPDATE orders
        SET vendor_id = (
            SELECT id FROM vendors WHERE name_zh = '（舊資料）未知店家'
        )
        WHERE vendor_id IS NULL
        """
    )
    op.alter_column("orders", "vendor_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_orders_vendor_id_vendors"), "orders", "vendors", ["vendor_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema (keeps the data: names go back into the old columns)."""
    op.drop_constraint(
        op.f("fk_orders_vendor_id_vendors"), "orders", type_="foreignkey"
    )
    op.drop_column("orders", "vendor_id")
    op.add_column(
        "menu_items",
        sa.Column("vendor", sa.VARCHAR(length=100), nullable=True),
    )
    op.add_column(
        "menu_items",
        sa.Column("item_name", sa.VARCHAR(length=100), nullable=True),
    )
    op.execute(
        """
        UPDATE menu_items AS m
        SET vendor = v.name_zh, item_name = m.item_name_zh
        FROM vendors AS v
        WHERE v.id = m.vendor_id
        """
    )
    op.alter_column("menu_items", "vendor", nullable=False)
    op.alter_column("menu_items", "item_name", nullable=False)
    op.drop_constraint(
        op.f("fk_menu_items_vendor_id_vendors"), "menu_items", type_="foreignkey"
    )
    op.drop_column("menu_items", "prep_minutes")
    op.drop_column("menu_items", "category_en")
    op.drop_column("menu_items", "category_zh")
    op.drop_column("menu_items", "item_name_en")
    op.drop_column("menu_items", "item_name_zh")
    op.drop_column("menu_items", "vendor_id")
    op.drop_table("vendors")
