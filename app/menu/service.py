from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.menu import repo
from app.menu.models import MenuItem, Vendor
from app.menu.schemas import (
    MenuItemCreate,
    MenuItemUpdate,
    VendorCreate,
    VendorRead,
    VendorUpdate,
)

# Columns that may be emptied by sending null (the photos); null is ignored for the rest
_NULLABLE = {"image_url", "cover_image_url"}


def _apply(row: Vendor | MenuItem, changes: dict[str, object]) -> None:
    for field, value in changes.items():
        if value is not None or field in _NULLABLE:
            setattr(row, field, value)


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


def to_read(session: Session, vendors: Sequence[Vendor]) -> list[VendorRead]:
    """The API view of vendors, with how many orders each one has waiting."""
    counts = repo.queue_counts(session, [v.id for v in vendors])
    return [
        VendorRead.model_validate(v).model_copy(
            update={"queue_count": counts.get(v.id, 0)}
        )
        for v in vendors
    ]


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
    # Same rule as menu items: fields left out stay as they are; null is ignored
    # (those columns cannot be empty), except for the photos, where it removes them.
    _apply(vendor, data.model_dump(exclude_unset=True))
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
    # A field sent as null is ignored too (those columns cannot be empty),
    # except image_url, where null removes the photo.
    _apply(item, data.model_dump(exclude_unset=True))
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
