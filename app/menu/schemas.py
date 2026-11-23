from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

# Same 100-character limit as the columns in app/menu/models.py
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Price = Annotated[int, Field(ge=0, le=100_000)]  # NT dollars, whole numbers
Minutes = Annotated[int, Field(ge=0, le=180)]
# Same 500-character limit as the image_url columns
ImageUrl = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
# Ids of add-on groups and choices: short, and safe to join as "group:choice"
OptionId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,30}$")]

# Parts of campus; the home page has a tab for each (other: shown under "all" only)
AREAS = ("fengyun", "shuimu", "snack", "other")
Area = Literal["fengyun", "shuimu", "snack", "other"]

# The same text in both languages, as returned by the API
Localized = dict[str, str]


class LocalizedName(BaseModel):
    zh: Name
    en: Name


# ---------- Add-ons ----------
class OptionChoice(BaseModel):
    id: OptionId
    label: LocalizedName
    price_delta: Annotated[int, Field(ge=0, le=10_000)] = 0  # added to the item price


class OptionGroup(BaseModel):
    """One question on the item page, e.g. "Rice: regular / less".

    required groups take exactly one choice (the customer must pick one);
    the others take up to max_select choices, or none.
    """

    id: OptionId
    name: LocalizedName
    required: bool = False
    max_select: Annotated[int, Field(ge=1, le=20)] = 1
    choices: list[OptionChoice] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def check(self) -> Self:
        ids = [choice.id for choice in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError(f"group '{self.id}' has two choices with the same id")
        if self.required and self.max_select != 1:
            raise ValueError(f"required group '{self.id}' must have max_select 1")
        return self


OptionGroups = Annotated[list[OptionGroup], Field(max_length=10)]


def _unique_group_ids(groups: list[OptionGroup] | None) -> None:
    ids = [group.id for group in groups or []]
    if len(set(ids)) != len(ids):
        raise ValueError("two add-on groups have the same id")


# ---------- Vendors ----------
# A time of day in Taiwan, "HH:MM", on a 15-minute mark like the pickup slots
ClockTime = Annotated[
    str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):(00|15|30|45)$")
]


class PickupPeriod(BaseModel):
    """One stretch of the day in which customers can book a pickup, e.g.
    11:00-13:30; both ends can be booked. The same every day."""

    open: ClockTime
    close: ClockTime

    @model_validator(mode="after")
    def _open_before_close(self) -> Self:
        # "HH:MM" strings compare in time order
        if self.open >= self.close:
            raise ValueError("a pickup period must close after it opens")
        return self


# Empty: the vendor takes bookings at any time (still 30 minutes to 24 hours ahead)
PickupHours = Annotated[list[PickupPeriod], Field(max_length=6)]


class VendorCreate(BaseModel):
    name_zh: Name
    name_en: Name
    description_zh: str = ""
    description_en: str = ""
    opening_hours_zh: ShortText = ""
    opening_hours_en: ShortText = ""
    location_zh: ShortText = ""
    location_en: ShortText = ""
    area: Area = "other"
    is_accepting_orders: bool = True
    allow_scheduled_pickup: bool = True
    pickup_hours: PickupHours = []
    image_url: ImageUrl | None = None
    cover_image_url: ImageUrl | None = None


class VendorUpdate(BaseModel):
    """PATCH body: only the fields that are sent get changed.

    null is ignored, except for the photos, where it removes the photo.
    """

    name_zh: Name | None = None
    name_en: Name | None = None
    description_zh: str | None = None
    description_en: str | None = None
    opening_hours_zh: ShortText | None = None
    opening_hours_en: ShortText | None = None
    location_zh: ShortText | None = None
    location_en: ShortText | None = None
    area: Area | None = None
    is_accepting_orders: bool | None = None
    allow_scheduled_pickup: bool | None = None
    pickup_hours: PickupHours | None = None  # [] removes the limit
    image_url: ImageUrl | None = None
    cover_image_url: ImageUrl | None = None


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Localized
    description: Localized
    opening_hours: Localized
    location: Localized
    area: str
    is_accepting_orders: bool
    allow_scheduled_pickup: bool
    pickup_hours: list[PickupPeriod]
    image_url: str | None
    cover_image_url: str | None
    # Orders waiting at this vendor right now (confirming or preparing). Filled in
    # by the vendor endpoints; the frontend uses it for the wait estimate.
    queue_count: int = 0


# ---------- Menu items ----------
class MenuItemCreate(BaseModel):
    vendor_id: int
    item_name_zh: Name
    item_name_en: Name
    category_zh: Name
    category_en: Name
    description_zh: LongText = ""
    description_en: LongText = ""
    price: Price
    prep_minutes: Minutes
    is_available: bool = True
    image_url: ImageUrl | None = None
    option_groups: OptionGroups = []

    @model_validator(mode="after")
    def check_groups(self) -> Self:
        _unique_group_ids(self.option_groups)
        return self


class MenuItemUpdate(BaseModel):
    """PATCH body: only the fields that are sent get changed.

    null is ignored, except for image_url, where it removes the photo.
    """

    vendor_id: int | None = None
    item_name_zh: Name | None = None
    item_name_en: Name | None = None
    category_zh: Name | None = None
    category_en: Name | None = None
    description_zh: LongText | None = None
    description_en: LongText | None = None
    price: Price | None = None
    prep_minutes: Minutes | None = None
    is_available: bool | None = None
    image_url: ImageUrl | None = None
    option_groups: OptionGroups | None = None

    @model_validator(mode="after")
    def check_groups(self) -> Self:
        _unique_group_ids(self.option_groups)
        return self


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    item_name: Localized
    category: Localized
    description: Localized
    price: int
    prep_minutes: int
    is_available: bool
    image_url: str | None
    option_groups: list[OptionGroup]
