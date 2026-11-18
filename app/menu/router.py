from collections.abc import Sequence

from fastapi import APIRouter, status

from app.auth.dependencies import DbSession, StaffUser
from app.menu import service
from app.menu.models import MenuItem, Vendor
from app.menu.schemas import (
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    VendorCreate,
    VendorRead,
    VendorUpdate,
)

router = APIRouter(tags=["menu"])


# ---------- Public: anyone (admins included) can browse vendors and the menu ----------
@router.get("/vendors", response_model=list[VendorRead])
def list_vendors(session: DbSession) -> Sequence[Vendor]:
    return service.list_vendors(session)


# Declared before /vendors/{vendor_id} so "me" is not read as an id
@router.get("/vendors/me", response_model=VendorRead)
def get_my_vendor(session: DbSession, staff: StaffUser) -> Vendor:
    return service.get_own_vendor(session, staff)


@router.get("/vendors/{vendor_id}", response_model=VendorRead)
def get_vendor(vendor_id: int, session: DbSession) -> Vendor:
    return service.get_vendor(session, vendor_id)


@router.get("/menu-items", response_model=list[MenuItemRead])
def list_menu_items(
    session: DbSession, vendor_id: int | None = None, available_only: bool = False
) -> Sequence[MenuItem]:
    return service.list_items(
        session, vendor_id=vendor_id, available_only=available_only
    )


@router.get("/menu-items/{item_id}", response_model=MenuItemRead)
def get_menu_item(item_id: int, session: DbSession) -> MenuItem:
    return service.get_item(session, item_id)


# ---------- Vendor staff only: manage their own vendor and its menu ----------
# Admins only monitor, so they get 403 on everything below.
@router.post("/vendors", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def register_vendor(data: VendorCreate, session: DbSession, staff: StaffUser) -> Vendor:
    return service.register_vendor(session, staff, data)


@router.patch("/vendors/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int, data: VendorUpdate, session: DbSession, staff: StaffUser
) -> Vendor:
    return service.update_vendor(session, staff, vendor_id, data)


@router.post(
    "/menu-items", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED
)
def create_menu_item(
    data: MenuItemCreate, session: DbSession, staff: StaffUser
) -> MenuItem:
    return service.create_item(session, staff, data)


@router.patch("/menu-items/{item_id}", response_model=MenuItemRead)
def update_menu_item(
    item_id: int, data: MenuItemUpdate, session: DbSession, staff: StaffUser
) -> MenuItem:
    return service.update_item(session, staff, item_id, data)


@router.delete("/menu-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(item_id: int, session: DbSession, staff: StaffUser) -> None:
    service.delete_item(session, staff, item_id)
