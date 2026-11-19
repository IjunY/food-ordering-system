from app.auth.schemas import UserRegister


class StaffCreate(UserRegister):
    """An admin creating a vendor staff account.

    Same fields and rules as customer sign-up. The admin chooses the first
    password and hands it to the vendor; the vendor has to replace it
    (POST /api/auth/change-password) before doing anything else. The new account
    has no vendor yet: after that it registers one with POST /api/vendors.
    """
