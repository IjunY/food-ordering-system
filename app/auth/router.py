from fastapi import APIRouter, Request, status

from app.auth import service
from app.auth.dependencies import CurrentUser, DbSession
from app.auth.models import User
from app.auth.schemas import TokenResponse, UserLogin, UserRead, UserRegister
from app.auth.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, session: DbSession) -> User:
    return service.register_user(session, data)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, session: DbSession) -> TokenResponse:
    user = service.authenticate(session, data.student_id, data.password)
    token = create_access_token(user.id, request.app.state.app_settings)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
