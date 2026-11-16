from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import repo
from app.auth.models import User
from app.auth.schemas import UserRegister
from app.auth.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.auth.states import UserRole
from app.core.errors import ConflictError, UnauthorizedError


def register_user(
    session: Session, data: UserRegister, role: UserRole = UserRole.CUSTOMER
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
