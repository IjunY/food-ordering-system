from collections.abc import Sequence

from fastapi import APIRouter, status

from app.admin import service
from app.admin.schemas import StaffCreate
from app.auth.dependencies import AdminUser, DbSession
from app.auth.models import User
from app.auth.schemas import UserRead

# Admins monitor vendors, menus and orders through the normal read endpoints.
# The one thing they create is vendor staff accounts, since sign-up only makes customers.
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/staff", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_staff(data: StaffCreate, session: DbSession, _admin: AdminUser) -> User:
    return service.create_staff(session, data)


@router.get("/staff", response_model=list[UserRead])
def list_staff(session: DbSession, _admin: AdminUser) -> Sequence[User]:
    return service.list_staff(session)
