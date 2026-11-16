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
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
