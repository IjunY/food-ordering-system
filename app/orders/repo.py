from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.orders.models import Order
from app.orders.states import OrderStatus


def add(session: Session, order: Order) -> Order:
    session.add(order)  # the OrderItems in order.items are saved along with it
    session.flush()
    return order


def get(session: Session, order_id: int, for_update: bool = False) -> Order | None:
    query = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    if for_update:
        # Locks the row until commit, so two status changes cannot interleave
        query = query.with_for_update()
    return session.scalar(query)


def list_orders(
    session: Session,
    created_by: str | None = None,
    status: OrderStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Order]:
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if created_by is not None:
        query = query.where(Order.created_by == created_by)
    if status is not None:
        query = query.where(Order.status == status)
    return session.scalars(query).all()
