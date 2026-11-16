from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.states import UserRole
from app.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.menu import repo as menu_repo
from app.orders import repo
from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate, OrderItemRead, OrderRead
from app.orders.states import ALLOWED_TRANSITIONS, OrderStatus


def _is_staff(user: User) -> bool:
    return user.role in (UserRole.STAFF, UserRole.ADMIN)


def create_order(session: Session, user: User, data: OrderCreate) -> Order:
    # The same item listed twice becomes one line with the quantities added up
    quantities: dict[int, int] = {}
    for line in data.items:
        quantities[line.item_id] = quantities.get(line.item_id, 0) + line.quantity

    menu_items = {m.id: m for m in menu_repo.get_many(session, quantities)}
    for item_id in quantities:
        menu_item = menu_items.get(item_id)
        if menu_item is None:
            raise NotFoundError(f"Menu item {item_id} does not exist")
        if not menu_item.is_available:
            raise ConflictError(f"'{menu_item.item_name}' is not available right now")
    if len({m.vendor for m in menu_items.values()}) > 1:
        raise BadRequestError("An order can only contain items from one vendor")

    order = Order(
        created_by=user.student_id,
        items=[
            # unit_price is copied now so later menu price changes do not alter this order
            OrderItem(
                item_id=item_id, quantity=quantity, unit_price=menu_items[item_id].price
            )
            for item_id, quantity in quantities.items()
        ],
    )
    repo.add(session, order)
    session.commit()
    return order


def get_order(
    session: Session, user: User, order_id: int, for_update: bool = False
) -> Order:
    order = repo.get(session, order_id, for_update=for_update)
    # Someone else's order looks the same as a missing one, so order ids cannot be probed
    if order is None or (order.created_by != user.student_id and not _is_staff(user)):
        raise NotFoundError("Order not found")
    return order


def list_orders(
    session: Session,
    user: User,
    mine: bool = False,
    status: OrderStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Order]:
    # Customers only ever see their own orders; staff see everyone's unless mine=true
    only_own = mine or not _is_staff(user)
    return repo.list_orders(
        session,
        created_by=user.student_id if only_own else None,
        status=status,
        limit=limit,
        offset=offset,
    )


def _change_status(session: Session, order: Order, new_status: OrderStatus) -> Order:
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise ConflictError(
            f"Cannot change an order from '{order.status.value}' to '{new_status.value}'"
        )
    order.status = new_status
    session.commit()
    return order


def update_status(
    session: Session, user: User, order_id: int, new_status: OrderStatus
) -> Order:
    """Staff moving an order forward (or cancelling it)."""
    order = get_order(session, user, order_id, for_update=True)
    return _change_status(session, order, new_status)


def cancel_order(session: Session, user: User, order_id: int) -> Order:
    order = get_order(session, user, order_id, for_update=True)
    # Once the kitchen has started, only staff can cancel.
    # (Finished or already-cancelled orders fall through to the 409 in _change_status.)
    if not _is_staff(user) and order.status in (
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ):
        raise ForbiddenError(
            "This order is already being prepared and can no longer be cancelled"
        )
    return _change_status(session, order, OrderStatus.CANCELLED)


def to_read(session: Session, orders: Sequence[Order]) -> list[OrderRead]:
    """Builds the API response, adding item names, vendor and totals from the menu."""
    item_ids = {item.item_id for order in orders for item in order.items}
    menu_items = {m.id: m for m in menu_repo.get_many(session, item_ids)}

    result = []
    for order in orders:
        lines = [
            OrderItemRead(
                id=item.id,
                item_id=item.item_id,
                item_name=menu_items[item.item_id].item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.quantity * item.unit_price,
            )
            for item in sorted(order.items, key=lambda i: i.id)
        ]
        result.append(
            OrderRead(
                id=order.id,
                status=order.status,
                created_at=order.created_at,
                created_by=order.created_by,
                # one order = one vendor (checked in create_order)
                vendor=menu_items[order.items[0].item_id].vendor if order.items else "",
                items=lines,
                total=sum(line.subtotal for line in lines),
            )
        )
    return result
