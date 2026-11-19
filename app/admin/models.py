from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import User
from app.core.db import Base


class Admin(Base):
    """Profile of a platform admin: one row per user whose role is ADMIN.

    Who may act as an admin is still decided by ``users.role`` (that is what the
    permission checks read). This table only holds what is specific to admins,
    so sign-in and roles stay in one place. Create rows with
    ``app.admin.service.grant_admin``, which sets the role and adds the row together.
    """

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique: a user has at most one admin profile.
    # CASCADE: deleting the user removes the profile with it.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    display_name: Mapped[str] = mapped_column(String(100))
    # The admin who granted this; None for the first admin (created by a script)
    # or when that admin's account was deleted later.
    granted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Two foreign keys point at users, so each relationship names its column
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    granted_by: Mapped[User | None] = relationship(foreign_keys=[granted_by_id])
