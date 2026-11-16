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


def get_current_user(
    request: Request,
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not signed in")
    user_id = decode_access_token(
        credentials.credentials, request.app.state.app_settings
    )
    user = repo.get_by_id(session, user_id) if user_id is not None else None
    if user is None:
        raise UnauthorizedError("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory: only lets the listed roles through."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to do this")
        return user

    return checker


# Vendor staff and platform admins
StaffUser = Annotated[User, Depends(require_roles(UserRole.STAFF, UserRole.ADMIN))]
