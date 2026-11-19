from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings

_ALGORITHM = "HS256"
_hasher = PasswordHasher()

# Verified against when the account does not exist, so a wrong student ID
# takes as long as a wrong password and cannot be told apart by timing.
DUMMY_PASSWORD_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, settings: Settings, *, token_version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "ver": token_version,  # must match users.token_version when the token is used
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=_ALGORITHM
    )


def decode_access_token(token: str, settings: Settings) -> tuple[int, int] | None:
    """Returns (user id, token version) from a valid token, or None if it is bad,
    expired, or from before token versions existed."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "exp", "ver"]},
        )
        return int(payload["sub"]), int(payload["ver"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
