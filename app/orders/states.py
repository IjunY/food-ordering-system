from enum import Enum


class OrderStatus(Enum):
    CONFIRMING = "confirming"
    PREPARING = "preparing"
    READY = "ready"
    PICKED_UP = "picked up"
    CANCELLED = "cancelled"


# Which status an order may move to next. Anything not listed is rejected.
# confirming -> preparing -> ready -> picked up, and cancelling is possible until pick-up.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CONFIRMING: frozenset({OrderStatus.PREPARING, OrderStatus.CANCELLED}),
    OrderStatus.PREPARING: frozenset({OrderStatus.READY, OrderStatus.CANCELLED}),
    OrderStatus.READY: frozenset({OrderStatus.PICKED_UP, OrderStatus.CANCELLED}),
    OrderStatus.PICKED_UP: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}
