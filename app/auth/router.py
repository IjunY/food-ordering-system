from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.auth import service
from app.auth.dependencies import DbSession, SignedInUser
from app.auth.emails import password_reset_email
from app.auth.models import User
from app.auth.schemas import (
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.auth.security import create_access_token
from app.mail.sender import Mailer, get_mailer, send_quietly

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
    """Every token issued before this stops working; use the one returned here.

    An account created by an admin (must_choose_username) also sends
    new_student_id here, the first time, to pick its own login ID.
    """
    user = service.change_password(
        session, user, data.current_password, data.new_password, data.new_student_id
    )
    return _token_response(user, request)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    data: PasswordResetRequest,
    request: Request,
    session: DbSession,
    background: BackgroundTasks,
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> None:
    """Emails a reset link to the account with this login ID or email.

    The answer is the same whether or not the account exists, and the email goes
    out after the response, so neither the reply nor its timing gives that away.
    """
    settings = request.app.state.app_settings
    minutes = settings.password_reset_minutes
    found = service.request_password_reset(
        session, data.account, timedelta(minutes=minutes)
    )
    if found is not None:
        user, token = found
        link = f"{settings.app_url.rstrip('/')}/#reset-{token}"
        background.add_task(
            send_quietly, mailer, password_reset_email(user, link, minutes)
        )


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(
    data: PasswordResetConfirm, request: Request, session: DbSession
) -> TokenResponse:
    """Sets the new password from an emailed link and signs the user in."""
    user = service.reset_password(session, data.token, data.new_password)
    return _token_response(user, request)


def _token_response(user: User, request: Request) -> TokenResponse:
    token = create_access_token(
        user.id, request.app.state.app_settings, token_version=user.token_version
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))
