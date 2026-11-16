from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Same 100-character limit as the columns in app/menu/models.py
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Price = Annotated[int, Field(ge=0, le=100_000)]  # NT dollars, whole numbers


class MenuItemCreate(BaseModel):
    vendor: Name
    item_name: Name
    price: Price
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    """PATCH body: only the fields that are sent get changed."""

    vendor: Name | None = None
    item_name: Name | None = None
    price: Price | None = None
    is_available: bool | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    item_name: str
    price: int
    is_available: bool
