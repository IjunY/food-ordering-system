"""orders point at the account that placed them by id (foreign key), not by login ID

orders.created_by (the customer's student_id, as text) becomes orders.user_id, a
foreign key to users.id. Existing orders are matched to their account by
student_id. If an order matches no account the upgrade stops and lists those
orders, instead of guessing an owner or deleting them.

Revision ID: b7e2a4c9d815
Revises: a8d3f5c2e7b1
Create Date: 2026-11-23 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2a4c9d815"
down_revision: str | Sequence[str] | None = "a8d3f5c2e7b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE orders SET user_id = users.id FROM users "
        "WHERE users.student_id = orders.created_by"
    )
    orphans = (
        op.get_bind()
        .execute(sa.text("SELECT id, created_by FROM orders WHERE user_id IS NULL"))
        .all()
    )
    if orphans:
        listed = ", ".join(f"order {id} ({who!r})" for id, who in orphans[:20])
        raise RuntimeError(
            f"{len(orphans)} order(s) match no account by student_id: {listed}. "
            "Point them at an account (or delete them) and run the upgrade again."
        )
    op.alter_column("orders", "user_id", nullable=False)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_orders_user_id_users"), "orders", "users", ["user_id"], ["id"]
    )
    op.drop_column("orders", "created_by")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "orders", sa.Column("created_by", sa.String(length=100), nullable=True)
    )
    op.execute(
        "UPDATE orders SET created_by = users.student_id FROM users "
        "WHERE users.id = orders.user_id"
    )
    op.alter_column("orders", "created_by", nullable=False)
    op.drop_constraint(op.f("fk_orders_user_id_users"), "orders", type_="foreignkey")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_column("orders", "user_id")
