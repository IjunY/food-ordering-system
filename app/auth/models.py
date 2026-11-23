from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, false, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    # The vendor a STAFF account works for (one vendor per staff account).
    # Always None for customers and admins. Set when the staff account registers
    # its vendor (POST /api/vendors) or by the seed script.
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"))
    # Set for accounts whose first password was chosen by someone else (an admin
    # creating a staff account). Until it is changed, the account can only read
    # /auth/me and change its password.
    must_change_password: Mapped[bool] = mapped_column(
        default=False, server_default=false()
    )
    # Set for accounts whose login ID an admin made up (vendor staff). At the first
    # sign-in the owner picks their own login ID along with their password; after
    # that the login ID never changes.
    must_choose_username: Mapped[bool] = mapped_column(
        default=False, server_default=false()
    )
    # Copied into every login token; bumping it (on a password change) makes all
    # tokens issued before then invalid, so a leaked password stops working at once.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PasswordReset(Base):
    """A "forgot password" link sent by email.

    Only a hash of the token is kept, so someone who can read the database still
    cannot use the links. A link works once, until expires_at; setting a new
    password closes every open link of that account.
    """

    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # SHA-256 (hex) of the token in the link
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship()


class EmailVerification(Base):
    """A sign-up code emailed to an address, to prove the address belongs to the
    person signing up. The account is only created once the right code comes back.

    Only a hash of the code is kept. A code works once, until expires_at, and only
    for MAX_CODE_ATTEMPTS wrong guesses (app/auth/service.py); sending a new code
    closes the older ones of that address.
    """

    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)  # lower case
    # SHA-256 (hex) of "<email>:<code>"
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Wrong codes tried against this one
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    # Set when the code was used, or closed by a newer code / too many wrong tries
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
