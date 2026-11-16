from collections.abc import Sequence

from fastapi import APIRouter, status

from app.auth.dependencies import DbSession, StaffUser
from app.menu import service
from app.menu.models import MenuItem
from app.menu.schemas import MenuItemCreate, MenuItemRead, MenuItemUpdate

router = APIRouter(tags=["menu"])


# ---------- Public: anyone can browse the menu ----------
@router.get("/vendors", response_model=list[str])
def list_vendors(session: DbSession) -> Sequence[str]:
    return service.list_vendors(session)


@router.get("/menu-items", response_model=list[MenuItemRead])
def list_menu_items(
    session: DbSession, vendor: str | None = None, available_only: bool = False
) -> Sequence[MenuItem]:
    return service.list_items(session, vendor=vendor, available_only=available_only)


@router.get("/menu-items/{item_id}", response_model=MenuItemRead)
def get_menu_item(item_id: int, session: DbSession) -> MenuItem:
    return service.get_item(session, item_id)


# ---------- Staff / admin only: manage the menu ----------
@router.post(
    "/menu-items", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED
)
def create_menu_item(
    data: MenuItemCreate, session: DbSession, _staff: StaffUser
) -> MenuItem:
    return service.create_item(session, data)


@router.patch("/menu-items/{item_id}", response_model=MenuItemRead)
def update_menu_item(
    item_id: int, data: MenuItemUpdate, session: DbSession, _staff: StaffUser
) -> MenuItem:
    return service.update_item(session, item_id, data)


@router.delete("/menu-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(item_id: int, session: DbSession, _staff: StaffUser) -> None:
    service.delete_item(session, item_id)
