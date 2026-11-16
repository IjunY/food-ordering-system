from datetime import datetime

from pydantic import BaseModel, Field

from app.orders.states import OrderStatus


class OrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0, le=99)


class OrderCreate(BaseModel):
    # Prices are not accepted from the client: the server copies them from the menu
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    id: int
    item_id: int
    item_name: str
    quantity: int
    unit_price: int  # price at the time of ordering
    subtotal: int


class OrderRead(BaseModel):
    id: int
    status: OrderStatus
    created_at: datetime
    created_by: str  # student_id of the customer
    vendor: str
    items: list[OrderItemRead]
    total: int
