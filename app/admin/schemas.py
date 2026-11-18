from app.auth.schemas import UserRegister


class StaffCreate(UserRegister):
    """An admin creating a vendor staff account.

    Same fields and rules as customer sign-up. The admin chooses the first
    password and hands it to the vendor. The new account has no vendor yet:
    after signing in it registers one with POST /api/vendors.
    """
