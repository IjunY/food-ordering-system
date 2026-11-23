from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from app.orders.states import OrderStatus

# "group:choice", e.g. "rice:less" (ids from the menu item's option_groups)
OptionRef = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,30}:[A-Za-z0-9_-]{1,30}$")
]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]


class OrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0, le=99)
    # Add-ons picked on the item page; every required group needs exactly one
    option_ids: list[OptionRef] = Field(default=[], max_length=40)
    note: Note = ""


class OrderCreate(BaseModel):
    # Prices are not accepted from the client: the server copies them from the menu
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)
    # None (or left out): pick up as soon as it is ready. Otherwise the booked time,
    # with a timezone ("2026-11-23T12:30:00+08:00"); rules in app/orders/pickup.py
    pickup_time: AwareDatetime | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    id: int
    item_id: int
    item_name: dict[str, str]
    quantity: int
    unit_price: int  # price at the time of ordering, add-ons included
    subtotal: int
    option_ids: list[str]
    # The add-ons as one line of text per language ("Less rice, No cutlery"); None without add-ons
    options_label: dict[str, str] | None
    note: str


class OrderRead(BaseModel):
    id: int
    status: OrderStatus
    created_at: datetime
    user_id: int  # the account that placed the order (User.id)
    vendor_id: int
    vendor_name: dict[str, str]  # {"zh": ..., "en": ...}
    items: list[OrderItemRead]
    total: int
    # The latest online payment for this order ("unpaid": none started yet)
    payment_status: Literal["unpaid", "pending", "paid", "failed", "expired"]
    pay_at_pickup: bool  # the customer will pay at the counter
    pickup_time: datetime | None  # booked pickup time; None = as soon as possible
