import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import repo
from app.auth.models import EmailVerification, PasswordReset, User
from app.auth.schemas import UserRegister, UserSignUp
from app.auth.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.auth.states import UserRole
from app.core.errors import (
    BadRequestError,
    ConflictError,
    TooManyRequestsError,
    UnauthorizedError,
)

# At most one reset email per account per minute, so the form cannot be used to
# flood someone's inbox
RESET_EMAIL_INTERVAL = timedelta(minutes=1)

# Sign-up codes: valid for 10 minutes, one email per address per minute, and a
# code stops working after 5 wrong tries (a new one has to be sent), so the
# 1,000,000 possible codes cannot be guessed
CODE_VALID_FOR = timedelta(minutes=10)
CODE_EMAIL_INTERVAL = timedelta(minutes=1)
MAX_CODE_ATTEMPTS = 5


def register_user(
    session: Session,
    data: UserRegister,
    role: UserRole = UserRole.CUSTOMER,
    must_change_password: bool = False,
    vendor_id: int | None = None,
    must_choose_username: bool = False,
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
        must_choose_username=must_choose_username,
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


def _hash_code(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()


def send_signup_code(session: Session, email: str, now: datetime | None = None) -> str:
    """Makes a new sign-up code for this address and returns it (to be emailed).

    Older codes of the address stop working. Refused when the address already
    has an account, or a code went out less than a minute ago.
    """
    now = now or datetime.now(UTC)
    email = email.lower()
    if repo.get_by_email(session, email) is not None:
        raise ConflictError("This email is already registered")
    last = repo.last_code_sent(session, email)
    if last is not None and now - last < CODE_EMAIL_INTERVAL:
        raise TooManyRequestsError(
            "A code was just sent to this email; wait a minute before asking again"
        )
    code = f"{secrets.randbelow(1_000_000):06d}"
    repo.close_verifications(session, email, now)
    repo.add_verification(
        session,
        EmailVerification(
            email=email,
            code_hash=_hash_code(email, code),
            created_at=now,
            expires_at=now + CODE_VALID_FOR,
        ),
    )
    session.commit()
    return code


def sign_up(session: Session, data: UserSignUp, now: datetime | None = None) -> User:
    """A customer creating an account with the code emailed to them."""
    now = now or datetime.now(UTC)
    email = data.email.lower()
    verification = repo.get_open_verification(session, email, now)
    if verification is None:
        raise BadRequestError(
            "The verification code has expired or was not sent; ask for a new one"
        )
    if not secrets.compare_digest(
        verification.code_hash, _hash_code(email, data.email_code)
    ):
        verification.attempts += 1
        if verification.attempts >= MAX_CODE_ATTEMPTS:
            verification.used_at = now  # too many wrong tries: a new code is needed
        session.commit()
        raise BadRequestError("The verification code is incorrect")
    verification.used_at = now
    # register_user commits the code as used together with the new account
    # (or rolls both back if the student ID / email was taken meanwhile)
    return register_user(session, data)


def authenticate(session: Session, student_id: str, password: str) -> User:
    user = repo.get_by_student_id(session, student_id.strip())
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    if not verify_password(password, password_hash) or user is None:
        # Same message for both cases so it does not reveal which IDs exist
        raise UnauthorizedError("Incorrect student ID or password")
    return user


def change_password(
    session: Session,
    user: User,
    current_password: str,
    new_password: str,
    new_student_id: str | None = None,
) -> User:
    """Sets a new password and signs out every other session.

    For an account that still has the login ID an admin made up
    (must_choose_username), this is also where its owner picks their own login ID;
    any other account keeps its login ID for good.

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

    if user.must_choose_username:
        if new_student_id is None:
            raise BadRequestError("Choose your own login ID")
        if new_student_id != user.student_id:
            if repo.get_by_student_id(session, new_student_id) is not None:
                raise ConflictError("This login ID is already taken")
            user.student_id = new_student_id
        user.must_choose_username = False
    elif new_student_id is not None and new_student_id != user.student_id:
        raise BadRequestError("A login ID cannot be changed")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version += 1
    repo.close_resets(session, user.id, datetime.now(UTC))
    try:
        session.commit()
    except IntegrityError as exc:
        # Someone else took the same login ID at the same moment
        session.rollback()
        raise ConflictError("This login ID is already taken") from exc
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def request_password_reset(
    session: Session, account: str, valid_for: timedelta, now: datetime | None = None
) -> tuple[User, str] | None:
    """Makes a reset link for the account with this login ID or email.

    Returns the account and the token to email, or None when there is nothing to
    send: no such account, or a link already went out in the last minute. The
    caller answers the same either way, so the form does not reveal which
    accounts exist.
    """
    now = now or datetime.now(UTC)
    account = account.strip()
    user = (
        repo.get_by_email(session, account.lower())
        if "@" in account
        else repo.get_by_student_id(session, account)
    )
    if user is None:
        return None
    last = repo.last_reset_sent(session, user.id)
    if last is not None and now - last < RESET_EMAIL_INTERVAL:
        return None

    token = secrets.token_hex(
        32
    )  # 256 random bits, hex so it fits the #reset-<token> route
    repo.add_reset(
        session,
        PasswordReset(
            user_id=user.id,
            token_hash=_hash_token(token),
            created_at=now,
            expires_at=now + valid_for,
        ),
    )
    session.commit()
    return user, token


def reset_password(
    session: Session, token: str, new_password: str, now: datetime | None = None
) -> User:
    """Sets a new password from an emailed link. The link then stops working, as do
    the account's other open links and every login token issued before."""
    now = now or datetime.now(UTC)
    reset = repo.get_open_reset(session, _hash_token(token), now)
    if reset is None:
        raise BadRequestError("This reset link is invalid or has expired")

    user = reset.user
    session.refresh(user, with_for_update=True)
    user.password_hash = hash_password(new_password)
    # They chose this password themselves, so no forced change after it.
    # must_choose_username stays: a vendor who has not picked a login ID yet
    # still does that at the next sign-in.
    user.must_change_password = False
    user.token_version += 1
    repo.close_resets(session, user.id, now)
    session.commit()
    return user
