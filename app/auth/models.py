from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.states import UserRole
from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The login name. Also what Order.created_by stores.
    student_id: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    # Argon2 hash, never the password itself
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False), default=UserRole.CUSTOMER
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
