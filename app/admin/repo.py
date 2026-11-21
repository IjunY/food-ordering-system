from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.models import Admin
from app.auth.models import User
from app.auth.states import UserRole
from app.orders.models import Order
from app.orders.states import OrderStatus


def get_by_user_id(session: Session, user_id: int) -> Admin | None:
    return session.scalar(select(Admin).where(Admin.user_id == user_id))


def add(session: Session, admin: Admin) -> Admin:
    session.add(admin)
    session.flush()  # sends the INSERT so the id (and any unique violation) shows up now
    return admin


def list_staff(session: Session) -> Sequence[User]:
    return session.scalars(
        select(User).where(User.role == UserRole.STAFF).order_by(User.id)
    ).all()


def staff_by_vendor(session: Session) -> dict[int, list[str]]:
    """vendor id -> login IDs of the staff accounts linked to it."""
    rows = session.execute(
        select(User.vendor_id, User.student_id)
        .where(User.role == UserRole.STAFF, User.vendor_id.is_not(None))
        .order_by(User.id)
    ).all()
    result: dict[int, list[str]] = {}
    for vendor_id, student_id in rows:
        if vendor_id is not None:  # always true here (filtered above); narrows the type
            result.setdefault(vendor_id, []).append(student_id)
    return result


def orders_since_by_vendor(session: Session, since: datetime) -> dict[int, int]:
    """vendor id -> orders placed since the given time, cancelled ones left out."""
    rows = session.execute(
        select(Order.vendor_id, func.count())
        .where(Order.created_at >= since, Order.status != OrderStatus.CANCELLED)
        .group_by(Order.vendor_id)
    ).all()
    return {vendor_id: count for vendor_id, count in rows}


def count_customers(session: Session) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.CUSTOMER)
        )
        or 0
    )
