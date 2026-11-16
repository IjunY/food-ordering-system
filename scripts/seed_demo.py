"""Fills the database with demo data so the frontend can be tried end to end.

    uv run python scripts/seed_demo.py --password <password for the demo accounts>

- Menu: scripts/demo_menu.json, which is the frontend's demo menu
  (frontend/js/mock/data.js). The frontend still shows menus from its own demo
  data and matches them to these rows by vendor + item name when ordering, so
  the two files must list the same names.
- Accounts: a customer (112012345), a vendor staff account (staff) and an
  admin (admin), all with the password given on the command line.

Running it again only adds what is missing; nothing is changed or deleted.
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import repo as user_repo
from app.auth.schemas import UserRegister
from app.auth.service import register_user
from app.auth.states import UserRole
from app.core.config import get_settings
from app.core.db import get_engine
from app.menu.models import MenuItem

MENU_FILE = Path(__file__).with_name("demo_menu.json")

DEMO_ACCOUNTS = [
    ("112012345", UserRole.CUSTOMER),
    ("staff", UserRole.STAFF),
    ("admin", UserRole.ADMIN),
]


def seed_menu(session: Session, rows: list[dict]) -> int:
    existing = {
        (vendor, name)
        for vendor, name in session.execute(
            select(MenuItem.vendor, MenuItem.item_name)
        ).all()
    }
    added = 0
    for row in rows:
        if (row["vendor"], row["item_name"]) in existing:
            continue
        session.add(MenuItem(**row))
        added += 1
    session.commit()
    return added


def seed_accounts(session: Session, password: str) -> int:
    added = 0
    for student_id, role in DEMO_ACCOUNTS:
        if user_repo.get_by_student_id(session, student_id) is not None:
            continue
        register_user(
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
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--password", required=True, help="password for the demo accounts"
    )
    args = parser.parse_args()

    rows = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    engine = get_engine(get_settings())
    with sessionmaker(bind=engine)() as session:
        menu_added = seed_menu(session, rows)
        accounts_added = seed_accounts(session, args.password)
    engine.dispose()
    print(f"menu items added: {menu_added}, accounts added: {accounts_added}")


if __name__ == "__main__":
    main()
