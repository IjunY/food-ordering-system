"""Fills the database with demo data so the frontend can be tried end to end.

    uv run python scripts/seed_demo.py --password <password for the demo accounts>

- Vendors and menu: scripts/demo_menu.json, which is the frontend's demo data
  (frontend/js/mock/data.js). The frontend still shows menus from its own demo
  data and matches them to these rows by vendor + item name (Chinese) when
  ordering, so the two files must list the same names.
- Accounts: a customer (112012345), a vendor staff account (staff) and an
  admin (admin, with its row in the admins table), all with the password given
  on the command line.

Running it again only adds what is missing; nothing is changed or deleted.
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.admin import repo as admin_repo
from app.admin.service import grant_admin
from app.auth import repo as user_repo
from app.auth.schemas import UserRegister
from app.auth.service import register_user
from app.auth.states import UserRole
from app.core.config import get_settings
from app.core.db import get_engine
from app.menu.models import MenuItem, Vendor
from app.menu.schemas import MenuItemCreate, VendorCreate

MENU_FILE = Path(__file__).with_name("demo_menu.json")

DEMO_ACCOUNTS = [
    ("112012345", UserRole.CUSTOMER),
    ("staff", UserRole.STAFF),
    ("admin", UserRole.ADMIN),
]


def seed_vendors(session: Session, rows: list[dict]) -> int:
    """Adds the vendors that are not there yet (matched by Chinese name)."""
    existing = set(session.scalars(select(Vendor.name_zh)).all())
    added = 0
    for row in rows:
        data = VendorCreate.model_validate(row)
        if data.name_zh in existing:
            continue
        session.add(Vendor(**data.model_dump()))
        existing.add(data.name_zh)
        added += 1
    session.commit()
    return added


def seed_menu(session: Session, rows: list[dict]) -> int:
    """Adds the menu items that are not there yet.

    Each row names its vendor by the vendor's Chinese name ("vendor"), since the
    vendor ids are only known once the vendors are in the database.
    """
    vendor_ids = dict(session.execute(select(Vendor.name_zh, Vendor.id)).all())
    existing: set[tuple[int, str]] = {
        (vendor_id, name)
        for vendor_id, name in session.execute(
            select(MenuItem.vendor_id, MenuItem.item_name_zh)
        ).all()
    }
    added = 0
    for row in rows:
        fields = {key: value for key, value in row.items() if key != "vendor"}
        if row["vendor"] not in vendor_ids:
            raise ValueError(f"Unknown vendor {row['vendor']!r}; seed vendors first")
        data = MenuItemCreate.model_validate(
            {**fields, "vendor_id": vendor_ids[row["vendor"]]}
        )
        if (data.vendor_id, data.item_name_zh) in existing:
            continue
        session.add(MenuItem(**data.model_dump()))
        existing.add((data.vendor_id, data.item_name_zh))
        added += 1
    session.commit()
    return added


def seed_accounts(session: Session, password: str) -> int:
    added = 0
    for student_id, role in DEMO_ACCOUNTS:
        user = user_repo.get_by_student_id(session, student_id)
        if user is None:
            user = register_user(
                session,
                UserRegister(
                    student_id=student_id,
                    email=f"{student_id}@example.com",
                    phone_number="0900000000",
                    password=password,
                ),
                role=role,
            )
            added += 1
        # Also fills in the profile for an admin seeded before the admins table existed
        if (
            role is UserRole.ADMIN
            and admin_repo.get_by_user_id(session, user.id) is None
        ):
            grant_admin(session, user, display_name="Demo admin")
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--password", required=True, help="password for the demo accounts"
    )
    args = parser.parse_args()

    demo = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    engine = get_engine(get_settings())
    with sessionmaker(bind=engine)() as session:
        vendors_added = seed_vendors(session, demo["vendors"])
        menu_added = seed_menu(session, demo["items"])
        accounts_added = seed_accounts(session, args.password)
    engine.dispose()
    print(
        f"vendors added: {vendors_added}, menu items added: {menu_added}, "
        f"accounts added: {accounts_added}"
    )


if __name__ == "__main__":
    main()
