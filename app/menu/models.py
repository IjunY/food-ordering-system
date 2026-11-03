from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor: Mapped[str] = mapped_column(String(100))
    item_name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column()
    is_available: Mapped[bool] = mapped_column(default=True)
