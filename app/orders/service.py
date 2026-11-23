from collections.abc import Sequence
from typing import Any

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
from app.menu.models import MenuItem
from app.orders import repo
from app.orders.models import Order, OrderItem
from app.orders.pickup import check_pickup_time
from app.orders.schemas import OrderCreate, OrderItemRead, OrderRead
from app.orders.states import ALLOWED_TRANSITIONS, OrderStatus
from app.payments import refunds
from app.payments import repo as payments_repo
from app.payments.provider import PaymentProvider


def _manages(user: User, order: Order) -> bool:
    """True for the staff of the vendor the order was placed with."""
    return (
        user.role is UserRole.STAFF
        and user.vendor_id is not None
        and user.vendor_id == order.vendor_id
    )


def _can_see(user: User, order: Order) -> bool:
    # Admins monitor every order; staff see their own vendor's; everyone sees their own
    return (
        order.user_id == user.id or user.role is UserRole.ADMIN or _manages(user, order)
    )


def _pick_options(
    menu_item: MenuItem, option_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Checks the add-ons picked for one order line against the item's option groups.

    Returns them as they are stored on the order line (names and prices copied
    from the menu, in menu order).
    """
    groups = {group["id"]: group for group in menu_item.option_groups}
    picked: dict[str, set[str]] = {}
    for ref in option_ids:
        group_id, choice_id = ref.split(":", 1)
        group = groups.get(group_id)
        if group is None or all(c["id"] != choice_id for c in group["choices"]):
            raise BadRequestError(f"'{menu_item.item_name_zh}' has no add-on '{ref}'")
        picked.setdefault(group_id, set()).add(choice_id)

    options = []
    for group in menu_item.option_groups:
        chosen = picked.get(group["id"], set())
        if group.get("required") and len(chosen) != 1:
            raise BadRequestError(
                f"Pick one option for '{group['name']['zh']}' ({menu_item.item_name_zh})"
            )
        if len(chosen) > group.get("max_select", 1):
            raise BadRequestError(
                f"Too many options for '{group['name']['zh']}' ({menu_item.item_name_zh})"
            )
        options += [
            {
                "id": f"{group['id']}:{choice['id']}",
                "group": group["name"],
                "label": choice["label"],
                "price_delta": choice.get("price_delta", 0),
            }
            for choice in group["choices"]
            if choice["id"] in chosen
        ]
    return options


def create_order(session: Session, user: User, data: OrderCreate) -> Order:
    # The same item with the same add-ons and note, listed twice, becomes one line
    # with the quantities added up
    quantities: dict[tuple[int, tuple[str, ...], str], int] = {}
    for line in data.items:
        key = (line.item_id, tuple(sorted(set(line.option_ids))), line.note)
        quantities[key] = quantities.get(key, 0) + line.quantity

    item_ids = {item_id for item_id, _, _ in quantities}
    menu_items = {m.id: m for m in menu_repo.get_many(session, item_ids)}
    for item_id in item_ids:
        menu_item = menu_items.get(item_id)
        if menu_item is None:
            raise NotFoundError(f"Menu item {item_id} does not exist")
        if not menu_item.is_available:
            raise ConflictError(
                f"'{menu_item.item_name_zh}' is not available right now"
            )
    if len({m.vendor_id for m in menu_items.values()}) > 1:
        raise BadRequestError("An order can only contain items from one vendor")
    # every item has the same vendor (checked just above)
    vendor_id = next(iter(menu_items.values())).vendor_id
    vendor = menu_repo.get_vendor(session, vendor_id)
    if vendor is None or not vendor.is_accepting_orders:
        raise ConflictError("This vendor is not taking orders right now")
    pickup_time = (
        None if data.pickup_time is None else check_pickup_time(data.pickup_time)
    )

    lines = []
    for (item_id, option_ids, note), quantity in quantities.items():
        menu_item = menu_items[item_id]
        options = _pick_options(menu_item, option_ids)
        # unit_price is copied now so later menu price changes do not alter this order
        unit_price = menu_item.price + sum(o["price_delta"] for o in options)
        lines.append(
            OrderItem(
                item_id=item_id,
                quantity=quantity,
                unit_price=unit_price,
                options=options,
                note=note,
            )
        )
    order = Order(
        user_id=user.id,
        vendor_id=vendor_id,
        items=lines,
        pickup_time=pickup_time,
    )
    repo.add(session, order)
    session.commit()
    return order


def get_order(
    session: Session, user: User, order_id: int, for_update: bool = False
) -> Order:
    order = repo.get(session, order_id, for_update=for_update)
    # Someone else's order looks the same as a missing one, so order ids cannot be probed
    if order is None or not _can_see(user, order):
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
    # mine=true: only orders this account placed, whatever its role.
    # Otherwise admins see every order, staff see their vendor's, customers their own.
    user_id: int | None = None
    vendor_id: int | None = None
    if mine:
        user_id = user.id
    elif user.role is UserRole.ADMIN:
        pass
    elif user.role is UserRole.STAFF and user.vendor_id is not None:
        vendor_id = user.vendor_id
    else:
        user_id = user.id
    return repo.list_orders(
        session,
        user_id=user_id,
        vendor_id=vendor_id,
        status=status,
        limit=limit,
        offset=offset,
    )


def _change_status(
    session: Session,
    order: Order,
    new_status: OrderStatus,
    provider: PaymentProvider,
) -> Order:
    """Moves the order on (the caller has locked its row). A cancelled order that was
    paid online is refunded first; if the refund fails, nothing changes (502).
    """
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise ConflictError(
            f"Cannot change an order from '{order.status.value}' to '{new_status.value}'"
        )
    if new_status is OrderStatus.CANCELLED:
        refunds.refund_order(session, provider, order.id)
    order.status = new_status
    session.commit()
    return order


def update_status(
    session: Session,
    user: User,
    order_id: int,
    new_status: OrderStatus,
    provider: PaymentProvider,
) -> Order:
    """The vendor's staff moving an order forward (or cancelling it)."""
    order = get_order(session, user, order_id, for_update=True)
    if not _manages(user, order):
        # e.g. staff looking at an order they placed themselves at another vendor
        raise ForbiddenError("Only the vendor's staff can change this order")
    return _change_status(session, order, new_status, provider)


def cancel_order(
    session: Session, user: User, order_id: int, provider: PaymentProvider
) -> Order:
    """Cancels the order; if it was paid online, the payment is refunded in full."""
    order = get_order(session, user, order_id, for_update=True)
    if not _manages(user, order):
        if order.user_id != user.id:
            # Only admins get here (anyone else could not see the order): they monitor only
            raise ForbiddenError("Admins can view orders but not change them")
        # Once the kitchen has started, only the vendor's staff can cancel.
        # (Finished or already-cancelled orders fall through to the 409 in _change_status.)
        if order.status in (OrderStatus.PREPARING, OrderStatus.READY):
            raise ForbiddenError(
                "This order is already being prepared and can no longer be cancelled"
            )
    return _change_status(session, order, OrderStatus.CANCELLED, provider)


def choose_pay_at_pickup(session: Session, user: User, order_id: int) -> Order:
    """The customer will pay at the counter instead of online; the order then shows
    up on the vendor's board as unpaid."""
    order = get_order(session, user, order_id, for_update=True)
    if order.user_id != user.id:
        # staff and admins can see the order, but only the customer decides how to pay
        raise ForbiddenError("Only the customer who placed the order can choose this")
    if order.status is not OrderStatus.CONFIRMING:
        raise ConflictError("This order is no longer waiting for payment")
    if payments_repo.has_paid_payment(session, order.id):
        raise ConflictError("This order is already paid")
    order.pay_at_pickup = True
    session.commit()
    return order


def _options_label(options: list[dict[str, Any]]) -> dict[str, str] | None:
    if not options:
        return None
    return {
        "zh": "、".join(option["label"]["zh"] for option in options),
        "en": ", ".join(option["label"]["en"] for option in options),
    }


def to_read(session: Session, orders: Sequence[Order]) -> list[OrderRead]:
    """Builds the API response, adding item names, vendor and totals from the menu."""
    item_ids = {item.item_id for order in orders for item in order.items}
    menu_items = {m.id: m for m in menu_repo.get_many(session, item_ids)}
    vendor_ids = {order.vendor_id for order in orders}
    vendors = {v.id: v for v in menu_repo.get_vendors(session, vendor_ids)}
    payment_status = {
        order_id: status.value
        for order_id, status in payments_repo.latest_status_by_order(
            session, [o.id for o in orders]
        ).items()
    }

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
                option_ids=[option["id"] for option in item.options],
                options_label=_options_label(item.options),
                note=item.note,
            )
            for item in sorted(order.items, key=lambda i: i.id)
        ]
        result.append(
            OrderRead(
                id=order.id,
                status=order.status,
                created_at=order.created_at,
                user_id=order.user_id,
                vendor_id=order.vendor_id,
                vendor_name=vendors[order.vendor_id].name,
                items=lines,
                total=sum(line.subtotal for line in lines),
                payment_status=payment_status.get(order.id, "unpaid"),
                pay_at_pickup=order.pay_at_pickup,
                pickup_time=order.pickup_time,
            )
        )
    return result
