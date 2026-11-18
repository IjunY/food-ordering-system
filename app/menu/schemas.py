from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Same 100-character limit as the columns in app/menu/models.py
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
Price = Annotated[int, Field(ge=0, le=100_000)]  # NT dollars, whole numbers
Minutes = Annotated[int, Field(ge=0, le=180)]

# The same text in both languages, as returned by the API
Localized = dict[str, str]


# ---------- Vendors ----------
class VendorCreate(BaseModel):
    name_zh: Name
    name_en: Name
    description_zh: str = ""
    description_en: str = ""
    opening_hours_zh: ShortText = ""
    opening_hours_en: ShortText = ""
    location_zh: ShortText = ""
    location_en: ShortText = ""
    is_accepting_orders: bool = True


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Localized
    description: Localized
    opening_hours: Localized
    location: Localized
    is_accepting_orders: bool


# ---------- Menu items ----------
class MenuItemCreate(BaseModel):
    vendor_id: int
    item_name_zh: Name
    item_name_en: Name
    category_zh: Name
    category_en: Name
    price: Price
    prep_minutes: Minutes
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    """PATCH body: only the fields that are sent get changed."""

    vendor_id: int | None = None
    item_name_zh: Name | None = None
    item_name_en: Name | None = None
    category_zh: Name | None = None
    category_en: Name | None = None
    price: Price | None = None
    prep_minutes: Minutes | None = None
    is_available: bool | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    item_name: Localized
    category: Localized
    price: int
    prep_minutes: int
    is_available: bool
