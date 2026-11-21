from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import repo
from app.auth.models import User
from app.auth.security import decode_access_token
from app.auth.states import UserRole
from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError

# auto_error=False: a missing header goes through our own 401 below instead of FastAPI's
_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_signed_in_user(
    request: Request,
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Any valid login, even one that still has to change its password."""
    if credentials is None:
        raise UnauthorizedError("Not signed in")
    claims = decode_access_token(
        credentials.credentials, request.app.state.app_settings
    )
    user = repo.get_by_id(session, claims[0]) if claims is not None else None
    # A token from before the last password change no longer counts
    if user is None or claims is None or claims[1] != user.token_version:
        raise UnauthorizedError("Invalid or expired token")
    return user


# Only for /auth/me and /auth/change-password: the two things an account that must
# change its password (or pick its login ID) is still allowed to do.
SignedInUser = Annotated[User, Depends(get_signed_in_user)]


def get_current_user(user: SignedInUser) -> User:
    if user.must_change_password or user.must_choose_username:
        raise ForbiddenError("Set up your login before continuing")
    return user


# What every other endpoint uses
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory: only lets the listed roles through."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to do this")
        return user

    return checker


# Vendor staff only. Admins can monitor (read everything) but not change vendors,
# menus or orders, so they are deliberately not let through here.
StaffUser = Annotated[User, Depends(require_roles(UserRole.STAFF))]

# Platform admins: read-only monitoring, plus creating vendor staff accounts
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
