from fastapi import APIRouter, Request, status

from app.auth import service
from app.auth.dependencies import DbSession, SignedInUser
from app.auth.models import User
from app.auth.schemas import (
    PasswordChange,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.auth.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, session: DbSession) -> User:
    return service.register_user(session, data)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, session: DbSession) -> TokenResponse:
    user = service.authenticate(session, data.student_id, data.password)
    return _token_response(user, request)


# SignedInUser, not CurrentUser: both stay usable while a password change is due
@router.get("/me", response_model=UserRead)
def me(user: SignedInUser) -> User:
    return user


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    data: PasswordChange, request: Request, session: DbSession, user: SignedInUser
) -> TokenResponse:
    """Every token issued before this stops working; use the one returned here."""
    user = service.change_password(
        session, user, data.current_password, data.new_password
    )
    return _token_response(user, request)


def _token_response(user: User, request: Request) -> TokenResponse:
    token = create_access_token(
        user.id, request.app.state.app_settings, token_version=user.token_version
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))
