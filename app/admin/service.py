from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin import repo
from app.admin.models import Admin
from app.auth.models import User
from app.auth.states import UserRole
from app.core.errors import ConflictError


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
