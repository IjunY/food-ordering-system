from sqlalchemy import ForeignKey, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Text shown to users is stored twice, once per language (<field>_zh / <field>_en).
# The API returns each pair as one {"zh": ..., "en": ...} object (the properties
# below), and the frontend shows whichever language the user picked.


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    description_zh: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    opening_hours_zh: Mapped[str] = mapped_column(String(100))
    opening_hours_en: Mapped[str] = mapped_column(String(100))
    location_zh: Mapped[str] = mapped_column(String(100))
    location_en: Mapped[str] = mapped_column(String(100))
    is_accepting_orders: Mapped[bool] = mapped_column(
        default=True, server_default=true()
    )
    # Photo for the vendor card; a path under the frontend (e.g. /img/...) or a URL
    image_url: Mapped[str | None] = mapped_column(String(500))

    @property
    def name(self) -> dict[str, str]:
        return {"zh": self.name_zh, "en": self.name_en}

    @property
    def description(self) -> dict[str, str]:
        return {"zh": self.description_zh, "en": self.description_en}

    @property
    def opening_hours(self) -> dict[str, str]:
        return {"zh": self.opening_hours_zh, "en": self.opening_hours_en}

    @property
    def location(self) -> dict[str, str]:
        return {"zh": self.location_zh, "en": self.location_en}


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    item_name_zh: Mapped[str] = mapped_column(String(100))
    item_name_en: Mapped[str] = mapped_column(String(100))
    category_zh: Mapped[str] = mapped_column(String(100))
    category_en: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column()
    prep_minutes: Mapped[int] = mapped_column()
    is_available: Mapped[bool] = mapped_column(default=True)
    image_url: Mapped[str | None] = mapped_column(String(500))

    @property
    def item_name(self) -> dict[str, str]:
        return {"zh": self.item_name_zh, "en": self.item_name_en}

    @property
    def category(self) -> dict[str, str]:
        return {"zh": self.category_zh, "en": self.category_en}
