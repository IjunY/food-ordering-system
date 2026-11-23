"""The demo data loader (scripts/seed_demo.py), which the container runs on its first start."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.admin import repo as admin_repo
from app.auth import repo as user_repo
from app.auth.states import UserRole
from app.menu.models import MenuItem, Vendor
from scripts import seed_demo

PASSWORD = "demo-password-123"
DEMO = json.loads(seed_demo.MENU_FILE.read_text(encoding="utf-8"))


def test_the_stalls_menus_and_demo_accounts_are_loaded(client: TestClient) -> None:
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        seed_demo.seed(session, PASSWORD)

        names = set(session.scalars(select(Vendor.name_zh)))
        assert {v["name_zh"] for v in DEMO["vendors"]} <= names
        roles = {
            account: user_repo.get_by_student_id(session, account)
            for account, _ in seed_demo.DEMO_ACCOUNTS
        }
        # No student account: students sign up themselves
        assert {a: u.role for a, u in roles.items() if u} == {
            "staff": UserRole.STAFF,
            "admin": UserRole.ADMIN,
        }
        # The admin can use the admin pages; the staff account runs the demo vendor
        assert admin_repo.get_by_user_id(session, roles["admin"].id) is not None  # type: ignore[union-attr]
        staff_vendor = session.get(Vendor, roles["staff"].vendor_id)  # type: ignore[union-attr]
        assert staff_vendor is not None
        assert staff_vendor.name_zh == seed_demo.DEMO_STAFF_VENDOR


def test_the_demo_vendor_is_one_of_the_stalls_in_the_file() -> None:
    # A typo here (e.g. 碳 for 炭) would leave the staff account without a vendor
    names = {v["name_zh"] for v in DEMO["vendors"]}
    assert seed_demo.DEMO_STAFF_VENDOR in names
    assert any(i["vendor"] == seed_demo.DEMO_STAFF_VENDOR for i in DEMO["items"])


def test_a_mistyped_demo_vendor_stops_the_seed_before_writing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(seed_demo, "DEMO_STAFF_VENDOR", "碳烤小姐")
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        before = session.scalar(select(func.count()).select_from(Vendor))
        with pytest.raises(ValueError, match="not a vendor"):
            seed_demo.seed(session, PASSWORD)
        assert session.scalar(select(func.count()).select_from(Vendor)) == before


def test_restarting_keeps_changes_made_in_the_app(client: TestClient) -> None:
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        seed_demo.seed(session, PASSWORD)
        row = next(
            i for i in DEMO["items"] if i["vendor"] == seed_demo.DEMO_STAFF_VENDOR
        )
        item = session.scalars(
            select(MenuItem)
            .join(Vendor)
            .where(
                Vendor.name_zh == row["vendor"],
                MenuItem.item_name_zh == row["item_name_zh"],
            )
        ).one()
        # The vendor changed the price and marked it sold out in the app
        item.price = row["price"] + 7
        item.is_available = False
        session.commit()

        # What the container does on every start: nothing, since there are vendors
        message = seed_demo.run(session, PASSWORD, if_empty=True)
        session.refresh(item)
        assert "leaving it as it is" in message
        assert (item.price, item.is_available) == (row["price"] + 7, False)

        # Without --if-empty the file's values come back: the reason for the option
        seed_demo.run(session, PASSWORD)
        session.refresh(item)
        assert (item.price, item.is_available) == (row["price"], True)


def test_the_password_comes_from_the_option_or_demo_password(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    with pytest.raises(SystemExit) as missing:
        seed_demo.main([])
    assert missing.value.code == 2
    assert "set DEMO_PASSWORD" in capsys.readouterr().err

    # Too short for a sign-in password: a clear message instead of a traceback
    monkeypatch.setenv("DEMO_PASSWORD", "short")
    with pytest.raises(SystemExit):
        seed_demo.main(["--if-empty"])
    assert "8 to 128 characters" in capsys.readouterr().err
