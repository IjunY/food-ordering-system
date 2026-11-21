from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.auth.states import UserRole

StudentId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9]{4,20}$"),
]
# Digits with an optional leading "+", e.g. 0912345678 or +886912345678
PhoneNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9]{8,15}$"),
]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserRegister(BaseModel):
    student_id: StudentId
    email: EmailStr = Field(max_length=255)
    phone_number: PhoneNumber
    password: Password


class UserLogin(BaseModel):
    student_id: str = Field(max_length=20)
    password: str = Field(max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    email: str
    phone_number: str
    role: UserRole
    vendor_id: int | None  # staff only: the vendor this account manages
    # True: the frontend should send the user to "change password" first
    must_change_password: bool
    # True: on that same page the user also picks their own login ID (vendor staff
    # whose first login ID came from an admin)
    must_choose_username: bool
    created_at: datetime


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: Password
    # The login ID the user picks. Only accepted while must_choose_username is set
    # (and then required); after that a login ID cannot change.
    new_student_id: StudentId | None = None


class PasswordResetRequest(BaseModel):
    # The login ID or the email address of the account
    account: str = Field(min_length=1, max_length=255)


class PasswordResetConfirm(BaseModel):
    # The token from the emailed link (#reset-<token>)
    token: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_password: Password


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
