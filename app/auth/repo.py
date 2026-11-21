from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth.models import PasswordReset, User


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


# ---- password reset links ----


def add_reset(session: Session, reset: PasswordReset) -> PasswordReset:
    session.add(reset)
    session.flush()
    return reset


def last_reset_sent(session: Session, user_id: int) -> datetime | None:
    return session.scalar(
        select(func.max(PasswordReset.created_at)).where(
            PasswordReset.user_id == user_id
        )
    )


def get_open_reset(
    session: Session, token_hash: str, now: datetime
) -> PasswordReset | None:
    """The unused, unexpired link with this token, locked until the commit so the
    same link cannot be used twice at once."""
    return session.scalar(
        select(PasswordReset)
        .where(
            PasswordReset.token_hash == token_hash,
            PasswordReset.used_at.is_(None),
            PasswordReset.expires_at > now,
        )
        .with_for_update()
    )


def close_resets(session: Session, user_id: int, now: datetime) -> None:
    """Marks every open link of this account as used."""
    session.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user_id, PasswordReset.used_at.is_(None))
        .values(used_at=now)
    )
