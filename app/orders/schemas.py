from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

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
    created_by: str  # student_id of the customer
    vendor_id: int
    vendor_name: dict[str, str]  # {"zh": ..., "en": ...}
    items: list[OrderItemRead]
    total: int
