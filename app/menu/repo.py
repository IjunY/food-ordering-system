from collections.abc import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.menu.models import MenuItem, Vendor
from app.orders.models import Order
from app.orders.states import OrderStatus


# ---------- Vendors ----------
def list_vendors(session: Session) -> Sequence[Vendor]:
    return session.scalars(select(Vendor).order_by(Vendor.id)).all()


def get_vendor(session: Session, vendor_id: int) -> Vendor | None:
    return session.get(Vendor, vendor_id)


def get_vendors(session: Session, vendor_ids: Iterable[int]) -> Sequence[Vendor]:
    ids = list(vendor_ids)
    if not ids:
        return []
    return session.scalars(select(Vendor).where(Vendor.id.in_(ids))).all()


def queue_counts(session: Session, vendor_ids: Iterable[int]) -> dict[int, int]:
    """vendor id -> orders still waiting there (confirming or preparing)."""
    ids = list(vendor_ids)
    if not ids:
        return {}
    rows = session.execute(
        select(Order.vendor_id, func.count())
        .where(
            Order.vendor_id.in_(ids),
            Order.status.in_([OrderStatus.CONFIRMING, OrderStatus.PREPARING]),
        )
        .group_by(Order.vendor_id)
    ).all()
    return {vendor_id: count for vendor_id, count in rows}


def add_vendor(session: Session, vendor: Vendor) -> Vendor:
    session.add(vendor)
    session.flush()  # sends the INSERT so the new id is known
    return vendor


# ---------- Menu items ----------
def list_items(
    session: Session, vendor_id: int | None = None, available_only: bool = False
) -> Sequence[MenuItem]:
    query = select(MenuItem).order_by(MenuItem.vendor_id, MenuItem.id)
    if vendor_id is not None:
        query = query.where(MenuItem.vendor_id == vendor_id)
    if available_only:
        query = query.where(MenuItem.is_available.is_(True))
    return session.scalars(query).all()


def get(session: Session, item_id: int) -> MenuItem | None:
    return session.get(MenuItem, item_id)


def get_many(session: Session, item_ids: Iterable[int]) -> Sequence[MenuItem]:
    ids = list(item_ids)
    if not ids:
        return []
    return session.scalars(select(MenuItem).where(MenuItem.id.in_(ids))).all()


def add(session: Session, item: MenuItem) -> MenuItem:
    session.add(item)
    session.flush()
    return item


def delete(session: Session, item: MenuItem) -> None:
    session.delete(item)
    session.flush()  # raises IntegrityError here if an order still points at the item
