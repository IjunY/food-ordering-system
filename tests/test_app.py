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
    DEMO_STAFF_VENDOR,
    MENU_FILE,
    close_other_vendors,
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


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def test_menu_file_is_valid() -> None:
    menu = json.loads(Path(MENU_FILE).read_text(encoding="utf-8"))
    assert menu["vendors"], "nthu_menu.json should list vendors"
    assert menu["items"], "nthu_menu.json should list menu items"
    vendor_names = set()
    for row in menu["vendors"]:
        vendor = VendorCreate.model_validate(row)
        vendor_names.add(vendor.name_zh)
        assert vendor.area != "other", row  # every NTHU vendor is on a campus tab
        assert vendor.image_url and (FRONTEND / vendor.image_url).is_file(), row
        cover = vendor.cover_image_url
        assert cover and (FRONTEND / cover).is_file(), row
    for row in menu["items"]:
        # items name their vendor; the seed script swaps that for the vendor's id
        assert row["vendor"] in vendor_names, row
        fields = {key: value for key, value in row.items() if key != "vendor"}
        # also checks the add-on groups (unique ids, required groups take one choice)
        item = MenuItemCreate.model_validate({**fields, "vendor_id": 1})
        assert item.image_url and (FRONTEND / item.image_url).is_file(), row
        assert item.description_zh and item.description_en, row


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
        # running again adds nothing ...
        assert seed_vendors(session, vendors) == 0
        assert seed_menu(session, items) == 0
        assert seed_accounts(session, "demo-password-1") == 0
        # ... but brings existing rows up to date with the file
        assert seed_vendors(session, [{**vendors[0], "location_zh": "風雲樓"}]) == 0
        assert seed_menu(session, [{**items[0], "price": 15}]) == 0
        updated = session.scalar(select(Vendor).where(Vendor.name_zh == "種子測試店"))
        assert updated is not None and updated.location_zh == "風雲樓"
        assert (
            session.scalar(
                select(MenuItem.price).where(
                    MenuItem.vendor_id == updated.id, MenuItem.item_name_zh == "甲"
                )
            )
            == 15
        )

        # --close-others: vendors not in the file stop taking orders, nothing is deleted
        old = Vendor(
            **VendorCreate(name_zh="舊示範店", name_en="Old Sample Vendor").model_dump()
        )
        session.add(old)
        session.flush()
        session.add(
            MenuItem(
                **MenuItemCreate(
                    vendor_id=old.id,
                    item_name_zh="丙",
                    item_name_en="C",
                    category_zh="主餐",
                    category_en="Mains",
                    price=30,
                    prep_minutes=5,
                ).model_dump()
            )
        )
        session.commit()
        assert close_other_vendors(session, ["種子測試店"]) >= 1
        session.refresh(old)
        session.refresh(updated)
        assert old.is_accepting_orders is False
        assert updated.is_accepting_orders is True
        assert (
            session.scalar(
                select(MenuItem.is_available).where(MenuItem.vendor_id == old.id)
            )
            is False
        )

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


def test_seeded_staff_manages_the_frontends_demo_vendor(client: TestClient) -> None:
    vendors = [{"name_zh": DEMO_STAFF_VENDOR, "name_en": "Mr. Beef"}]
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        session.execute(delete(User).where(User.student_id == "staff"))
        session.commit()
        seed_vendors(session, vendors)
        seed_accounts(session, "demo-password-1")
        staff = session.scalar(select(User).where(User.student_id == "staff"))
        vendor_id = session.scalar(
            select(Vendor.id).where(Vendor.name_zh == DEMO_STAFF_VENDOR)
        )
        assert staff is not None
        assert staff.vendor_id == vendor_id


def test_seed_moves_the_demo_staff_to_the_current_demo_vendor(
    client: TestClient,
) -> None:
    # Databases seeded by an older version have the demo staff on an old sample vendor
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        session.execute(delete(User).where(User.student_id == "staff"))
        session.commit()
        seed_vendors(
            session,
            [
                {"name_zh": "水木自助餐", "name_en": "Shuimu Buffet"},
                {"name_zh": DEMO_STAFF_VENDOR, "name_en": "Mr. Beef"},
            ],
        )
        seed_accounts(session, "demo-password-1")
        staff = session.scalar(select(User).where(User.student_id == "staff"))
        assert staff is not None
        staff.vendor_id = session.scalar(
            select(Vendor.id).where(Vendor.name_zh == "水木自助餐")
        )
        session.commit()

        seed_accounts(session, "demo-password-1")
        session.refresh(staff)
        assert staff.vendor_id == session.scalar(
            select(Vendor.id).where(Vendor.name_zh == DEMO_STAFF_VENDOR)
        )
