from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import repo
from app.auth.models import User
from app.auth.schemas import UserRegister
from app.auth.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.auth.states import UserRole
from app.core.errors import BadRequestError, ConflictError, UnauthorizedError


def register_user(
    session: Session,
    data: UserRegister,
    role: UserRole = UserRole.CUSTOMER,
    must_change_password: bool = False,
    vendor_id: int | None = None,
) -> User:
    email = data.email.lower()
    if repo.get_by_student_id(session, data.student_id) is not None:
        raise ConflictError("This student ID is already registered")
    if repo.get_by_email(session, email) is not None:
        raise ConflictError("This email is already registered")

    user = User(
        student_id=data.student_id,
        email=email,
        phone_number=data.phone_number,
        password_hash=hash_password(data.password),
        role=role,
        must_change_password=must_change_password,
        vendor_id=vendor_id,
    )
    try:
        repo.add(session, user)
        session.commit()
    except IntegrityError as exc:
        # Two sign-ups with the same ID/email at the same moment: the checks above
        # both pass, and the unique constraint stops the second one here.
        session.rollback()
        raise ConflictError("This student ID or email is already registered") from exc
    return user


def authenticate(session: Session, student_id: str, password: str) -> User:
    user = repo.get_by_student_id(session, student_id.strip())
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    if not verify_password(password, password_hash) or user is None:
        # Same message for both cases so it does not reveal which IDs exist
        raise UnauthorizedError("Incorrect student ID or password")
    return user


def change_password(
    session: Session, user: User, current_password: str, new_password: str
) -> User:
    """Sets a new password and signs out every other session.

    Bumping token_version invalidates all tokens issued so far, including the one
    used for this request; the router hands back a fresh token so this session
    carries on.
    """
    # Locks the row so two changes at once cannot both bump from the same version
    session.refresh(user, with_for_update=True)
    # 400, not 401: the frontend treats 401 as "signed out" and would drop the
    # session over a typo in the current password.
    if not verify_password(current_password, user.password_hash):
        raise BadRequestError("Current password is incorrect")
    if verify_password(new_password, user.password_hash):
        raise BadRequestError("The new password must be different from the current one")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version += 1
    session.commit()
    return user
