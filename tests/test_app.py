import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.admin.models import Admin
from app.auth.models import User
from app.auth.states import UserRole
from app.menu.models import MenuItem, Vendor
from app.menu.schemas import MenuItemCreate, VendorCreate
from scripts.seed_demo import (
    DEMO_ACCOUNTS,
    MENU_FILE,
    seed_accounts,
    seed_menu,
    seed_vendors,
)


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_is_served_at_root(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert '<script type="module" src="js/main.js">' in page.text

    script = client.get("/js/api.js")
    assert script.status_code == 200

    # API routes still win over the static files
    assert client.get("/api/menu-items").status_code == 200


def test_demo_menu_file_is_valid() -> None:
    demo = json.loads(Path(MENU_FILE).read_text(encoding="utf-8"))
    assert demo["vendors"], "demo_menu.json should list vendors"
    assert demo["items"], "demo_menu.json should list menu items"
    vendor_names = set()
    for row in demo["vendors"]:
        vendor_names.add(VendorCreate.model_validate(row).name_zh)
    for row in demo["items"]:
        # items name their vendor; the seed script swaps that for the vendor's id
        assert row["vendor"] in vendor_names, row
        fields = {key: value for key, value in row.items() if key != "vendor"}
        MenuItemCreate.model_validate({**fields, "vendor_id": 1})


def test_seed_is_idempotent(client: TestClient) -> None:
    vendors = [{"name_zh": "種子測試店", "name_en": "Seed Test Vendor"}]
    items = [
        {
            "vendor": "種子測試店",
            "item_name_zh": name_zh,
            "item_name_en": name_en,
            "category_zh": "主餐",
            "category_en": "Mains",
            "price": price,
            "prep_minutes": 5,
        }
        for name_zh, name_en, price in (("甲", "A", 10), ("乙", "B", 20))
    ]
    demo_ids = [student_id for student_id, _ in DEMO_ACCOUNTS]

    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        # start from no demo accounts (the local database may already be seeded;
        # everything here is rolled back after the test)
        session.execute(delete(User).where(User.student_id.in_(demo_ids)))
        session.commit()

        assert seed_vendors(session, vendors) == 1
        assert seed_menu(session, items) == 2
        assert seed_accounts(session, "demo-password-1") == 3
        # running again adds nothing
        assert seed_vendors(session, vendors) == 0
        assert seed_menu(session, items) == 0
        assert seed_accounts(session, "demo-password-1") == 0

        vendor_rows = session.scalar(
            select(func.count())
            .select_from(MenuItem)
            .join(Vendor, MenuItem.vendor_id == Vendor.id)
            .where(Vendor.name_en == "Seed Test Vendor")
        )
        assert vendor_rows == 2
        roles = dict(
            session.execute(
                select(User.student_id, User.role).where(User.student_id.in_(demo_ids))
            ).all()
        )
        assert roles == {
            "112012345": UserRole.CUSTOMER,
            "staff": UserRole.STAFF,
            "admin": UserRole.ADMIN,
        }
        # ... and the admin account has its profile row
        admin_profiles = session.scalar(
            select(func.count())
            .select_from(Admin)
            .join(User, Admin.user_id == User.id)
            .where(User.student_id == "admin")
        )
        assert admin_profiles == 1

    login = client.post(
        "/api/auth/login", json={"student_id": "staff", "password": "demo-password-1"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "staff"
