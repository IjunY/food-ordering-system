from enum import Enum


class UserRole(Enum):
    CUSTOMER = "customer"  # students ordering food (what registration creates)
    STAFF = "staff"  # vendor staff: manage the menu and move orders forward
    ADMIN = "admin"
