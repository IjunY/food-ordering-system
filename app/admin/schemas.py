from pydantic import BaseModel

from app.auth.schemas import UserRead, UserRegister
from app.menu.schemas import VendorCreate, VendorRead


class StaffCreate(UserRegister):
    """An admin creating a vendor staff account.

    Same fields and rules as customer sign-up. The admin chooses the first
    password and hands it to the vendor; the vendor has to replace it
    (POST /api/auth/change-password) before doing anything else. The new account
    has no vendor yet: after that it registers one with POST /api/vendors.
    """


class VendorWithStaffCreate(BaseModel):
    """An admin opening a new vendor: the store and the login that runs it, together.

    The staff account is linked to the new vendor and, like every account an admin
    creates, has to change its first password before it can do anything else.
    """

    vendor: VendorCreate
    staff: StaffCreate


class VendorWithStaffRead(BaseModel):
    vendor: VendorRead
    staff: UserRead


class AdminVendorRead(BaseModel):
    vendor: VendorRead
    staff_accounts: list[str]  # login IDs of the staff accounts that run it
    orders_today: int  # orders placed today (Taiwan time), cancelled ones left out


class AdminOverview(BaseModel):
    vendors: list[AdminVendorRead]
    customer_count: int  # registered customer accounts
    orders_today: int  # all vendors together, cancelled ones left out
