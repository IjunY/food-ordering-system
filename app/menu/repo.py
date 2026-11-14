from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.menu.models import MenuItem


def list_items(
    session: Session, vendor: str | None = None, available_only: bool = False
) -> Sequence[MenuItem]:
    query = select(MenuItem).order_by(MenuItem.vendor, MenuItem.id)
    if vendor is not None:
        query = query.where(MenuItem.vendor == vendor)
    if available_only:
        query = query.where(MenuItem.is_available.is_(True))
    return session.scalars(query).all()


def list_vendors(session: Session) -> Sequence[str]:
    return session.scalars(
        select(MenuItem.vendor).distinct().order_by(MenuItem.vendor)
    ).all()


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
