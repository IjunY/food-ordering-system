from enum import Enum


class OrderStatus(Enum):
    CONFIRMING = "confirming"
    PREPARING = "preparing"
    READY = "ready"
    PICKED_UP = "picked up"
    CANCELLED = "cancelled"
