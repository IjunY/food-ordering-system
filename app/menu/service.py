from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.menu import repo
from app.menu.models import MenuItem, Vendor
from app.menu.schemas import MenuItemCreate, MenuItemUpdate


# ---------- Vendors ----------
def list_vendors(session: Session) -> Sequence[Vendor]:
    return repo.list_vendors(session)


def get_vendor(session: Session, vendor_id: int) -> Vendor:
    vendor = repo.get_vendor(session, vendor_id)
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


# ---------- Menu items ----------
def list_items(
    session: Session, vendor_id: int | None = None, available_only: bool = False
) -> Sequence[MenuItem]:
    return repo.list_items(session, vendor_id=vendor_id, available_only=available_only)


def get_item(session: Session, item_id: int) -> MenuItem:
    item = repo.get(session, item_id)
    if item is None:
        raise NotFoundError("Menu item not found")
    return item


def create_item(session: Session, data: MenuItemCreate) -> MenuItem:
    # Checked here so a wrong id is a clear 404 instead of a foreign key error (500)
    get_vendor(session, data.vendor_id)
    item = repo.add(session, MenuItem(**data.model_dump()))
    session.commit()
    return item


def update_item(session: Session, item_id: int, data: MenuItemUpdate) -> MenuItem:
    item = get_item(session, item_id)
    if data.vendor_id is not None:
        get_vendor(session, data.vendor_id)
    # exclude_unset: fields left out of the request stay as they are.
    # A field sent as null is ignored too, since none of the columns can be empty.
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(item, field, value)
    session.commit()
    return item


def delete_item(session: Session, item_id: int) -> None:
    item = get_item(session, item_id)
    try:
        repo.delete(session, item)
        session.commit()
    except IntegrityError as exc:
        # order_items.item_id still references it; deleting would break past orders
        session.rollback()
        raise ConflictError(
            "This item appears in existing orders and cannot be deleted. "
            "Set is_available to false to take it off the menu instead."
        ) from exc
