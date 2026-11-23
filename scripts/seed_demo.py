"""Fills the database with the NTHU campus vendors and menus, plus demo accounts.

    uv run python -m scripts.seed_demo --password <password for the demo accounts>

(or set DEMO_PASSWORD instead of --password). With Docker this runs by itself on the
first start when DEMO_PASSWORD is set in .env: see scripts/docker-entrypoint.sh.

- Vendors and menu: scripts/nthu_menu.json (real stalls in Fengyun Hall, Shuimu
  Center and the Snack Bar; see the file's _comment for where the data came
  from), with their areas, photos, descriptions and add-on choices. The app
  shows vendors and menus from the database, so this file is where they start.
- Accounts: a vendor staff account (staff, managing DEMO_STAFF_VENDOR) and an
  admin (admin, with its row in the admins table), both with the password given
  on the command line (at least 8 characters). There is no student account:
  students sign up in the app. More vendors and their staff accounts can then
  be added by the admin in the app.

Running it again adds what is missing and brings vendors and items that are
already there (matched by Chinese name) up to date with the file. Nothing is
deleted. Vendors that are not in the file (e.g. the old sample vendors) stay as
they are, unless --close-others is given: then they stop taking orders and
their items go off the menu (past orders keep working).

With --if-empty it does nothing when the database already has vendors. The
container uses this on every start, so restarting never puts the stalls and
items back to the file's values over changes made in the app.
"""

import argparse
import json
import os
from collections.abc import Sequence
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

# The vendor the demo staff account manages: exactly a name_zh in nthu_menu.json
DEMO_STAFF_VENDOR = "炭烤小姐"

DEMO_ACCOUNTS = [
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


def has_vendors(session: Session) -> bool:
    return session.scalar(select(Vendor.id).limit(1)) is not None


def seed(session: Session, password: str, *, close_others: bool = False) -> str:
    """Loads the vendors, menu and demo accounts; returns a summary line."""
    demo = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    # Checked before writing anything: a name that matches no vendor would leave
    # the demo staff account without a vendor (it could not use the vendor pages)
    if DEMO_STAFF_VENDOR not in {v["name_zh"] for v in demo["vendors"]}:
        raise ValueError(
            f"DEMO_STAFF_VENDOR {DEMO_STAFF_VENDOR!r} is not a vendor in "
            f"{MENU_FILE.name}; use one of its name_zh values exactly"
        )
    vendors_added = seed_vendors(session, demo["vendors"])
    menu_added = seed_menu(session, demo["items"])
    closed = (
        close_other_vendors(session, [v["name_zh"] for v in demo["vendors"]])
        if close_others
        else 0
    )
    accounts_added = seed_accounts(session, password)
    return (
        f"vendors added: {vendors_added}, menu items added: {menu_added}, "
        f"accounts added: {accounts_added} (existing rows were updated to match "
        f"{MENU_FILE.name})"
        + (f", other vendors closed: {closed}" if close_others else "")
    )


def run(
    session: Session,
    password: str,
    *,
    if_empty: bool = False,
    close_others: bool = False,
) -> str:
    if if_empty and has_vendors(session):
        return "the database already has vendors, leaving it as it is"
    return seed(session, password, close_others=close_others)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--password",
        default=os.environ.get("DEMO_PASSWORD") or None,
        help="password for the demo accounts (default: the DEMO_PASSWORD variable)",
    )
    parser.add_argument(
        "--close-others",
        action="store_true",
        help="vendors not in the file stop taking orders and their items go off the menu",
    )
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="do nothing if the database already has vendors",
    )
    args = parser.parse_args(argv)
    if not args.password:
        parser.error("give --password or set DEMO_PASSWORD")
    if not 8 <= len(args.password) <= 128:
        # Same rule as sign-up; checked here so the error is clear (not a traceback)
        parser.error("the demo password must be 8 to 128 characters long")

    engine = get_engine(get_settings())
    with sessionmaker(bind=engine)() as session:
        message = run(
            session,
            args.password,
            if_empty=args.if_empty,
            close_others=args.close_others,
        )
    engine.dispose()
    print(f"Demo data: {message}")


if __name__ == "__main__":
    main()
