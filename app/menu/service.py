from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.menu import repo
from app.menu.models import MenuItem, Vendor
from app.menu.schemas import MenuItemCreate, MenuItemUpdate, VendorCreate, VendorUpdate


def _own_vendor_id(staff: User) -> int:
    """The vendor a staff account manages; staff without one cannot manage anything yet."""
    if staff.vendor_id is None:
        raise ForbiddenError("Register your vendor first (POST /api/vendors)")
    return staff.vendor_id


def _require_own_vendor(staff: User, vendor_id: int) -> None:
    if vendor_id != _own_vendor_id(staff):
        raise ForbiddenError("You can only manage your own vendor")


# ---------- Vendors ----------
def list_vendors(session: Session) -> Sequence[Vendor]:
    return repo.list_vendors(session)


def get_vendor(session: Session, vendor_id: int) -> Vendor:
    vendor = repo.get_vendor(session, vendor_id)
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


def get_own_vendor(session: Session, staff: User) -> Vendor:
    if staff.vendor_id is None:
        raise NotFoundError("This account has not registered a vendor yet")
    return get_vendor(session, staff.vendor_id)


def register_vendor(session: Session, staff: User, data: VendorCreate) -> Vendor:
    """A staff account creates its vendor and becomes the account that manages it."""
    # Locks the user row, so two sign-ups sent at once cannot both see "no vendor yet"
    session.refresh(staff, with_for_update=True)
    if staff.vendor_id is not None:
        raise ConflictError("This account already manages a vendor")
    vendor = repo.add_vendor(session, Vendor(**data.model_dump()))
    staff.vendor_id = vendor.id
    session.commit()
    return vendor


def update_vendor(
    session: Session, staff: User, vendor_id: int, data: VendorUpdate
) -> Vendor:
    vendor = get_vendor(session, vendor_id)
    _require_own_vendor(staff, vendor.id)
    # Same rule as menu items: fields left out stay as they are, and null is ignored
    # because none of the columns can be empty.
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(vendor, field, value)
    session.commit()
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


def create_item(session: Session, staff: User, data: MenuItemCreate) -> MenuItem:
    _require_own_vendor(staff, data.vendor_id)
    item = repo.add(session, MenuItem(**data.model_dump()))
    session.commit()
    return item


def update_item(
    session: Session, staff: User, item_id: int, data: MenuItemUpdate
) -> MenuItem:
    item = get_item(session, item_id)
    _require_own_vendor(staff, item.vendor_id)
    if data.vendor_id is not None:
        # Staff manage one vendor, so an item cannot be moved to someone else's
        _require_own_vendor(staff, data.vendor_id)
    # exclude_unset: fields left out of the request stay as they are.
    # A field sent as null is ignored too, since none of the columns can be empty.
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(item, field, value)
    session.commit()
    return item


def delete_item(session: Session, staff: User, item_id: int) -> None:
    item = get_item(session, item_id)
    _require_own_vendor(staff, item.vendor_id)
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
