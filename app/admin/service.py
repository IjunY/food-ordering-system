from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin import repo
from app.admin.models import Admin
from app.admin.schemas import (
    AdminOverview,
    AdminVendorRead,
    StaffCreate,
    VendorWithStaffCreate,
    VendorWithStaffRead,
)
from app.auth.models import User
from app.auth.schemas import UserRead
from app.auth.service import register_user
from app.auth.states import UserRole
from app.core.errors import ConflictError
from app.menu import repo as menu_repo
from app.menu import service as menu_service
from app.menu.models import Vendor

# Taiwan has no daylight saving time, so a fixed offset is enough for "today"
TAIWAN = timezone(timedelta(hours=8))


def grant_admin(
    session: Session, user: User, display_name: str, granted_by: User | None = None
) -> Admin:
    """Makes ``user`` an admin: sets the role and adds the profile in one commit,
    so there is never an admin profile for a non-admin (or the other way round)."""
    if repo.get_by_user_id(session, user.id) is not None:
        raise ConflictError("This user is already an admin")

    user.role = UserRole.ADMIN
    admin = Admin(
        user_id=user.id,
        display_name=display_name.strip(),
        granted_by_id=granted_by.id if granted_by is not None else None,
    )
    try:
        repo.add(session, admin)
        session.commit()
    except IntegrityError as exc:
        # Two grants for the same user at once: the unique user_id stops the second
        session.rollback()
        raise ConflictError("This user is already an admin") from exc
    return admin


def create_staff(session: Session, data: StaffCreate) -> User:
    """Creates a vendor staff account (no vendor yet; the staff registers it).

    The account must change its password before it can do anything else.

    Duplicate student IDs or emails raise the same 409 as customer sign-up.
    """
    # The admin knows this first password, so the staff member has to replace it
    return register_user(session, data, role=UserRole.STAFF, must_change_password=True)


def list_staff(session: Session) -> Sequence[User]:
    return repo.list_staff(session)


def create_vendor_with_staff(
    session: Session, data: VendorWithStaffCreate
) -> VendorWithStaffRead:
    """Opens a vendor and creates the staff account that runs it, in one transaction:
    if the login cannot be created (e.g. the ID is taken), no vendor is left behind."""
    vendor = menu_repo.add_vendor(session, Vendor(**data.vendor.model_dump()))
    try:
        staff = register_user(
            session,
            data.staff,
            role=UserRole.STAFF,
            must_change_password=True,
            vendor_id=vendor.id,
        )
    except ConflictError:
        session.rollback()  # also undoes the vendor added above
        raise
    return VendorWithStaffRead(
        vendor=menu_service.to_read(session, [vendor])[0],
        staff=UserRead.model_validate(staff),
    )


def overview(session: Session) -> AdminOverview:
    """Every vendor with its staff logins and today's orders, plus platform totals."""
    start_of_today = datetime.now(TAIWAN).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    vendors = menu_service.to_read(session, menu_service.list_vendors(session))
    staff = repo.staff_by_vendor(session)
    today = repo.orders_since_by_vendor(session, start_of_today)
    return AdminOverview(
        vendors=[
            AdminVendorRead(
                vendor=vendor,
                staff_accounts=staff.get(vendor.id, []),
                orders_today=today.get(vendor.id, 0),
            )
            for vendor in vendors
        ],
        customer_count=repo.count_customers(session),
        orders_today=sum(today.values()),
    )
