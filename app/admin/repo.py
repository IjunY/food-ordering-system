from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.models import Admin
from app.auth.models import User
from app.auth.states import UserRole


def get_by_user_id(session: Session, user_id: int) -> Admin | None:
    return session.scalar(select(Admin).where(Admin.user_id == user_id))


def add(session: Session, admin: Admin) -> Admin:
    session.add(admin)
    session.flush()  # sends the INSERT so the id (and any unique violation) shows up now
    return admin


def list_staff(session: Session) -> Sequence[User]:
    return session.scalars(
        select(User).where(User.role == UserRole.STAFF).order_by(User.id)
    ).all()
