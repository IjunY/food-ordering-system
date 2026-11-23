from typing import Annotated

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser, DbSession, StaffUser
from app.orders import service
from app.orders.schemas import OrderCreate, OrderRead, OrderStatusUpdate
from app.orders.states import OrderStatus
from app.payments.router import ProviderDep  # to refund paid orders that get cancelled

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, session: DbSession, user: CurrentUser) -> OrderRead:
    order = service.create_order(session, user, data)
    return service.to_read(session, [order])[0]


@router.get("", response_model=list[OrderRead])
def list_orders(
    session: DbSession,
    user: CurrentUser,
    mine: bool = False,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OrderRead]:
    orders = service.list_orders(
        session, user, mine=mine, status=status_filter, limit=limit, offset=offset
    )
    return service.to_read(session, orders)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, session: DbSession, user: CurrentUser) -> OrderRead:
    order = service.get_order(session, user, order_id)
    return service.to_read(session, [order])[0]


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    session: DbSession,
    staff: StaffUser,
    provider: ProviderDep,
) -> OrderRead:
    order = service.update_status(session, staff, order_id, data.status, provider)
    return service.to_read(session, [order])[0]


@router.post("/{order_id}/pay-at-pickup", response_model=OrderRead)
def pay_at_pickup(order_id: int, session: DbSession, user: CurrentUser) -> OrderRead:
    order = service.choose_pay_at_pickup(session, user, order_id)
    return service.to_read(session, [order])[0]


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int, session: DbSession, user: CurrentUser, provider: ProviderDep
) -> OrderRead:
    """Cancels the order. If it was paid online, the money is refunded first (502,
    and the order stays as it was, when the payment provider cannot refund it)."""
    order = service.cancel_order(session, user, order_id, provider)
    return service.to_read(session, [order])[0]
