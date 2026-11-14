import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.auth.models import User
from app.auth.states import UserRole
from app.menu.models import MenuItem
from app.menu.schemas import MenuItemCreate
from scripts.seed_demo import DEMO_ACCOUNTS, MENU_FILE, seed_accounts, seed_menu


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
    rows = json.loads(Path(MENU_FILE).read_text(encoding="utf-8"))
    assert rows, "demo_menu.json should not be empty"
    for row in rows:
        MenuItemCreate.model_validate(row)


def test_seed_is_idempotent(client: TestClient) -> None:
    rows = [
        {"vendor": "Seed Test Vendor", "item_name": "A", "price": 10},
        {"vendor": "Seed Test Vendor", "item_name": "B", "price": 20},
    ]
    demo_ids = [student_id for student_id, _ in DEMO_ACCOUNTS]

    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        # start from no demo accounts (the local database may already be seeded;
        # everything here is rolled back after the test)
        session.execute(delete(User).where(User.student_id.in_(demo_ids)))
        session.commit()

        assert seed_menu(session, rows) == 2
        assert seed_accounts(session, "demo-password-1") == 3
        # running again adds nothing
        assert seed_menu(session, rows) == 0
        assert seed_accounts(session, "demo-password-1") == 0

        vendor_rows = session.scalar(
            select(func.count())
            .select_from(MenuItem)
            .where(MenuItem.vendor == "Seed Test Vendor")
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

    login = client.post(
        "/api/auth/login", json={"student_id": "staff", "password": "demo-password-1"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "staff"
