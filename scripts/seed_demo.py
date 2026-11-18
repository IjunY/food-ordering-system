"""Fills the database with the NTHU campus vendors and menus, plus demo accounts.

    uv run python scripts/seed_demo.py --password <password for the demo accounts>

- Vendors and menu: scripts/nthu_menu.json (real stalls in Fengyun Hall, Shuimu
  Center and the Snack Bar; see the file's _comment for where the data came
  from). The frontend shows menus from frontend/js/mock/data.js and matches them
  to these rows by vendor + item name (Chinese) when ordering, so the two files
  must list the same names.
- Accounts: a customer (112012345), a vendor staff account (staff, managing
  牛肉先生, the vendor the frontend's demo staff account runs) and an admin
  (admin, with its row in the admins table), all with the password given on
  the command line.

Running it again adds what is missing and brings vendors and items that are
already there (matched by Chinese name) up to date with the file. Nothing is
deleted. Vendors that are not in the file (e.g. the old sample vendors) stay as
they are, unless --close-others is given: then they stop taking orders and
their items go off the menu (past orders keep working).
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select, update
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

MENU_FILE = Path(__file__).with_name("nthu_menu.json")

# The vendor the demo staff account manages (frontend/js/mock/data.js: USERS.staff -> r1)
DEMO_STAFF_VENDOR = "牛肉先生"

DEMO_ACCOUNTS = [
    ("112012345", UserRole.CUSTOMER),
    ("staff", UserRole.STAFF),
    ("admin", UserRole.ADMIN),
]


def seed_vendors(session: Session, rows: list[dict]) -> int:
    """Adds the vendors that are not there yet and updates the others.

    Vendors are matched by Chinese name. Returns how many were added.
    """
    existing = {v.name_zh: v for v in session.scalars(select(Vendor)).all()}
    added = 0
    for row in rows:
        data = VendorCreate.model_validate(row)
        vendor = existing.get(data.name_zh)
        if vendor is None:
            vendor = Vendor(**data.model_dump())
            session.add(vendor)
            existing[data.name_zh] = vendor
            added += 1
        else:
            for field, value in data.model_dump().items():
                setattr(vendor, field, value)
    session.commit()
    return added


def seed_menu(session: Session, rows: list[dict]) -> int:
    """Adds the menu items that are not there yet and updates the others.

    Each row names its vendor by the vendor's Chinese name ("vendor"), since the
    vendor ids are only known once the vendors are in the database. Items are
    matched by vendor + Chinese name. Returns how many were added.
    """
    vendor_ids = dict(session.execute(select(Vendor.name_zh, Vendor.id)).all())
    existing: dict[tuple[int, str], MenuItem] = {
        (item.vendor_id, item.item_name_zh): item
        for item in session.scalars(select(MenuItem)).all()
    }
    added = 0
    for row in rows:
        fields = {key: value for key, value in row.items() if key != "vendor"}
        if row["vendor"] not in vendor_ids:
            raise ValueError(f"Unknown vendor {row['vendor']!r}; seed vendors first")
        data = MenuItemCreate.model_validate(
            {**fields, "vendor_id": vendor_ids[row["vendor"]]}
        )
        key = (data.vendor_id, data.item_name_zh)
        item = existing.get(key)
        if item is None:
            item = MenuItem(**data.model_dump())
            session.add(item)
            existing[key] = item
            added += 1
        else:
            for field, value in data.model_dump().items():
                setattr(item, field, value)
    session.commit()
    return added


def close_other_vendors(session: Session, keep: list[str]) -> int:
    """Vendors not named in keep stop taking orders; their items go off the menu."""
    others = session.scalars(select(Vendor).where(Vendor.name_zh.not_in(keep))).all()
    for vendor in others:
        vendor.is_accepting_orders = False
    session.execute(
        update(MenuItem)
        .where(MenuItem.vendor_id.in_([v.id for v in others]))
        .values(is_available=False)
    )
    session.commit()
    return len(others)


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
        # Also fills in what accounts seeded by an older version of this script lack
        if (
            role is UserRole.ADMIN
            and admin_repo.get_by_user_id(session, user.id) is None
        ):
            grant_admin(session, user, display_name="Demo admin")
        # The demo staff account always manages DEMO_STAFF_VENDOR, also when an
        # older version of this script linked it to an earlier sample vendor
        if role is UserRole.STAFF:
            vendor_id = session.scalar(
                select(Vendor.id).where(Vendor.name_zh == DEMO_STAFF_VENDOR)
            )
            if vendor_id is not None and user.vendor_id != vendor_id:
                user.vendor_id = vendor_id
                session.commit()
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--password", required=True, help="password for the demo accounts"
    )
    parser.add_argument(
        "--close-others",
        action="store_true",
        help="vendors not in the file stop taking orders and their items go off the menu",
    )
    args = parser.parse_args()

    demo = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    engine = get_engine(get_settings())
    with sessionmaker(bind=engine)() as session:
        vendors_added = seed_vendors(session, demo["vendors"])
        menu_added = seed_menu(session, demo["items"])
        closed = (
            close_other_vendors(session, [v["name_zh"] for v in demo["vendors"]])
            if args.close_others
            else 0
        )
        accounts_added = seed_accounts(session, args.password)
    engine.dispose()
    print(
        f"vendors added: {vendors_added}, menu items added: {menu_added}, "
        f"accounts added: {accounts_added} (existing rows were updated to match "
        f"{MENU_FILE.name})"
        + (f", other vendors closed: {closed}" if args.close_others else "")
    )


if __name__ == "__main__":
    main()
