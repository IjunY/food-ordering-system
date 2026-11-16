from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_by_student_id(session: Session, student_id: str) -> User | None:
    return session.scalar(select(User).where(User.student_id == student_id))


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def add(session: Session, user: User) -> User:
    session.add(user)
    session.flush()  # sends the INSERT so the id (and any unique violation) shows up now
    return user
