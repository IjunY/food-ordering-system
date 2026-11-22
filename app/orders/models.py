from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    false,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.orders.states import OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, native_enum=False), default=OrderStatus.CONFIRMING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))

    created_by: Mapped[str] = mapped_column(String(100))

    # The customer chose to pay at the counter when picking up (no online payment).
    # Such orders go to the vendor's board as "unpaid, pay at counter".
    pay_at_pickup: Mapped[bool] = mapped_column(default=False, server_default=false())

    # The time the customer booked to pick up (on a 15-minute mark); None means
    # "as soon as possible". See app/orders/pickup.py for the rules.
    pickup_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Link between OrderItem.order
    # back_populates: adding an OrderItem to a list also makes the item belong to the order
    # "all, delete-orphan": Items are deleted when an order is deleted. Also, an item no longer belongs to an order when the item is deleted.
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    quantity: Mapped[int] = mapped_column()
    # Item price plus the add-ons picked, at the time of ordering
    unit_price: Mapped[int] = mapped_column()
    # The add-ons picked, copied from the menu when ordering (so later menu edits do
    # not change the order): [{"id": "group:choice", "group": {zh, en},
    # "label": {zh, en}, "price_delta": int}, ...]
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, server_default=text("'[]'")
    )
    # The customer's note for this line ("less onion"); empty when there is none
    note: Mapped[str] = mapped_column(String(60), default="", server_default="")

    # link between Order.items
    order: Mapped["Order"] = relationship(back_populates="items")
