from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from signup import sign_up
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin import repo
from app.admin.models import Admin
from app.admin.service import grant_admin
from app.auth.models import User
from app.auth.schemas import UserRegister
from app.auth.service import register_user
from app.auth.states import UserRole
from app.core.errors import ConflictError


@pytest.fixture
def session(client: TestClient) -> Iterator[Session]:
    # The client fixture rolls everything back after the test
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        yield session


def make_user(session: Session, student_id: str) -> User:
    return register_user(
        session,
        UserRegister(
            student_id=student_id,
            email=f"{student_id}@example.com",
            phone_number="0912345678",
            password="correct-horse-battery",
        ),
    )


def test_grant_admin_sets_the_role_and_adds_the_profile(session: Session) -> None:
    first = make_user(session, "admin0001")
    second = make_user(session, "admin0002")

    root = grant_admin(session, first, display_name="  Root Admin  ")
    granted = grant_admin(session, second, display_name="Ops", granted_by=first)

    assert first.role is UserRole.ADMIN
    assert second.role is UserRole.ADMIN
    assert root.display_name == "Root Admin"
    assert root.granted_by_id is None
    assert root.created_at is not None
    assert granted.granted_by_id == first.id

    session.expire_all()  # read back from the database, not the identity map
    profile = repo.get_by_user_id(session, second.id)
    assert profile is not None
    assert profile.user.student_id == "admin0002"
    assert profile.granted_by is not None
    assert profile.granted_by.student_id == "admin0001"


def test_a_user_has_at_most_one_admin_profile(session: Session) -> None:
    user = make_user(session, "admin0001")
    grant_admin(session, user, display_name="Root Admin")

    with pytest.raises(ConflictError):
        grant_admin(session, user, display_name="Again")

    # The database enforces it too, not only the service
    session.add(Admin(user_id=user.id, display_name="Duplicate"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_customers_have_no_admin_profile(session: Session) -> None:
    customer = make_user(session, "990000001")
    assert customer.role is UserRole.CUSTOMER
    assert repo.get_by_user_id(session, customer.id) is None


def test_deleting_users_keeps_the_table_consistent(session: Session) -> None:
    granter = make_user(session, "admin0001")
    grantee = make_user(session, "admin0002")
    grant_admin(session, granter, display_name="Root Admin")
    grant_admin(session, grantee, display_name="Ops", granted_by=granter)
    grantee_id = grantee.id

    # The granter's account goes away: the other admin keeps their profile
    session.execute(delete(User).where(User.id == granter.id))
    session.commit()
    session.expire_all()
    profile = repo.get_by_user_id(session, grantee_id)
    assert profile is not None
    assert profile.granted_by_id is None

    # The admin's own account goes away: the profile goes with it
    session.execute(delete(User).where(User.id == grantee_id))
    session.commit()
    assert session.scalar(select(Admin).where(Admin.user_id == grantee_id)) is None


# ---------- admins create vendor staff accounts ----------
NEW_STAFF = {
    "student_id": "staff01",
    "email": "Staff01@Example.com",
    "phone_number": "0912345678",
    "password": "first-password-123",
}


def test_admin_creates_a_staff_account_that_can_set_up_its_vendor(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)

    created = client.post("/api/admin/staff", json=NEW_STAFF, headers=admin)
    assert created.status_code == 201, created.text
    staff = created.json()
    assert staff["role"] == "staff"
    assert staff["student_id"] == "staff01"
    assert staff["email"] == "staff01@example.com"  # lower-cased, like sign-up
    assert staff["vendor_id"] is None
    assert "password" not in staff and "password_hash" not in staff

    # The admin can see it in the staff list (which may hold seeded accounts too)
    def listed() -> dict[str, dict]:
        rows = client.get("/api/admin/staff", headers=admin).json()
        return {row["student_id"]: row for row in rows}

    assert listed()["staff01"] == staff
    assert all(row["role"] == "staff" for row in listed().values())

    # The admin made up this login, so the account starts locked down
    assert staff["must_change_password"] is True
    assert staff["must_choose_username"] is True

    # The new account signs in with the password the admin chose ...
    login = client.post(
        "/api/auth/login",
        json={"student_id": "staff01", "password": NEW_STAFF["password"]},
    )
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True
    first = {"Authorization": f"Bearer {login.json()['access_token']}"}
    # ... can only see itself until the password is changed ...
    assert client.get("/api/auth/me", headers=first).status_code == 200
    blocked = client.post(
        "/api/vendors",
        json={"name_zh": "測試便當", "name_en": "Test Bento"},
        headers=first,
    )
    assert blocked.status_code == 403
    # Keeping the login ID the admin chose is fine, as long as it is a choice
    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": NEW_STAFF["password"],
            "new_password": "my-own-password-456",
            "new_student_id": "staff01",
        },
        headers=first,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["user"]["must_change_password"] is False
    assert changed.json()["user"]["must_choose_username"] is False
    headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    # ... and then registers its vendor
    vendor = client.post(
        "/api/vendors",
        json={"name_zh": "測試便當", "name_en": "Test Bento"},
        headers=headers,
    )
    assert vendor.status_code == 201, vendor.text
    assert listed()["staff01"]["vendor_id"] == vendor.json()["id"]


def test_staff_account_rules(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)
    assert client.post(
        "/api/admin/staff", json=NEW_STAFF, headers=admin
    ).status_code == (201)

    # Same uniqueness rules as sign-up
    assert client.post(
        "/api/admin/staff", json=NEW_STAFF, headers=admin
    ).status_code == (409)
    same_email = {**NEW_STAFF, "student_id": "staff02"}
    assert (
        client.post("/api/admin/staff", json=same_email, headers=admin).status_code
        == 409
    )
    # ... and the same validation
    for bad in ({"password": "short"}, {"email": "nope"}, {"student_id": "a b"}):
        response = client.post(
            "/api/admin/staff", json={**NEW_STAFF, **bad}, headers=admin
        )
        assert response.status_code == 422, bad

    # The role is fixed: a request cannot ask for an admin account
    sneaky = {**NEW_STAFF, "student_id": "staff03", "email": "s3@example.com"}
    made = client.post(
        "/api/admin/staff", json={**sneaky, "role": "admin"}, headers=admin
    )
    assert made.status_code == 201
    assert made.json()["role"] == "staff"


def test_only_admins_manage_staff_accounts(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    staff = auth_headers("staff09", UserRole.STAFF)
    customer = auth_headers("990000001")

    assert client.post("/api/admin/staff", json=NEW_STAFF).status_code == 401
    assert client.get("/api/admin/staff").status_code == 401
    for headers in (staff, customer):
        assert (
            client.post("/api/admin/staff", json=NEW_STAFF, headers=headers).status_code
            == 403
        )
        assert client.get("/api/admin/staff", headers=headers).status_code == 403


NEW_VENDOR = {
    "vendor": {
        "name_zh": "測試咖哩",
        "name_en": "Test Curry",
        "area": "shuimu",
        "location_zh": "水木 2F",
        "location_en": "Shuimu 2F",
    },
    "staff": {**NEW_STAFF, "student_id": "curry01", "email": "curry01@example.com"},
}


def test_admin_opens_a_vendor_with_its_staff_account(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)

    created = client.post("/api/admin/vendors", json=NEW_VENDOR, headers=admin)
    assert created.status_code == 201, created.text
    vendor, staff = created.json()["vendor"], created.json()["staff"]
    assert vendor["name"] == {"zh": "測試咖哩", "en": "Test Curry"}
    assert vendor["area"] == "shuimu"
    assert staff["role"] == "staff"
    assert staff["vendor_id"] == vendor["id"]
    assert staff["must_change_password"] is True
    assert staff["must_choose_username"] is True
    assert client.get(f"/api/vendors/{vendor['id']}").status_code == 200

    # The vendor signs in with the temporary login, picks its own login ID and
    # password, and can build its menu right away
    login = client.post(
        "/api/auth/login",
        json={"student_id": "curry01", "password": NEW_STAFF["password"]},
    ).json()
    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": NEW_STAFF["password"],
            "new_password": "curry-pass-789",
            "new_student_id": "currymaster",
        },
        headers={"Authorization": f"Bearer {login['access_token']}"},
    ).json()
    assert changed["user"]["student_id"] == "currymaster"
    headers = {"Authorization": f"Bearer {changed['access_token']}"}
    assert client.get("/api/vendors/me", headers=headers).json()["id"] == vendor["id"]
    item = client.post(
        "/api/menu-items",
        json={
            "vendor_id": vendor["id"],
            "item_name_zh": "咖哩飯",
            "item_name_en": "Curry Rice",
            "category_zh": "主餐",
            "category_en": "Mains",
            "price": 110,
            "prep_minutes": 7,
        },
        headers=headers,
    )
    assert item.status_code == 201, item.text

    # It shows up on the admin overview with its login
    overview = client.get("/api/admin/overview", headers=admin).json()
    row = next(v for v in overview["vendors"] if v["vendor"]["id"] == vendor["id"])
    assert row["staff_accounts"] == ["currymaster"]
    assert row["orders_today"] == 0


def test_vendor_is_not_created_when_its_login_cannot_be(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)
    auth_headers("curry01")  # the login ID is already taken

    taken = client.post("/api/admin/vendors", json=NEW_VENDOR, headers=admin)
    assert taken.status_code == 409
    names = [v["name"]["zh"] for v in client.get("/api/vendors").json()]
    assert "測試咖哩" not in names

    bad_area = {**NEW_VENDOR, "vendor": {**NEW_VENDOR["vendor"], "area": "moon"}}
    assert (
        client.post("/api/admin/vendors", json=bad_area, headers=admin).status_code
        == 422
    )


def test_overview_counts_todays_orders_and_customers(
    client: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    make_vendor: Callable[..., int],
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)
    before = client.get("/api/admin/overview", headers=admin).json()

    vendor_id = make_vendor("Overview Test", "總覽測試")
    staff = auth_headers("staff01", UserRole.STAFF, vendor_id=vendor_id)
    item_id = client.post(
        "/api/menu-items",
        json={
            "vendor_id": vendor_id,
            "item_name_zh": "飯",
            "item_name_en": "Rice",
            "category_zh": "主餐",
            "category_en": "Mains",
            "price": 10,
            "prep_minutes": 1,
        },
        headers=staff,
    ).json()["id"]
    customer = auth_headers("990000001")
    orders = [
        client.post(
            "/api/orders",
            json={"items": [{"item_id": item_id, "quantity": 1}]},
            headers=customer,
        ).json()["id"]
        for _ in range(2)
    ]
    client.post(f"/api/orders/{orders[1]}/cancel", headers=customer)

    after = client.get("/api/admin/overview", headers=admin).json()
    row = next(v for v in after["vendors"] if v["vendor"]["id"] == vendor_id)
    assert row["orders_today"] == 1  # the cancelled one is left out
    assert row["staff_accounts"] == ["staff01"]
    assert after["orders_today"] == before["orders_today"] + 1
    assert after["customer_count"] == before["customer_count"] + 1

    for headers in (staff, customer):
        assert client.get("/api/admin/overview", headers=headers).status_code == 403
        assert (
            client.post(
                "/api/admin/vendors", json=NEW_VENDOR, headers=headers
            ).status_code
            == 403
        )


def test_vendor_picks_its_login_id_once(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)
    auth_headers("taken01")  # someone else's login ID
    client.post("/api/admin/vendors", json=NEW_VENDOR, headers=admin)
    first = client.post(
        "/api/auth/login",
        json={"student_id": "curry01", "password": NEW_STAFF["password"]},
    ).json()
    temp = {"Authorization": f"Bearer {first['access_token']}"}

    def setup(**fields: str) -> int:
        body = {
            "current_password": NEW_STAFF["password"],
            "new_password": "curry-pass-789",
            **fields,
        }
        response = client.post("/api/auth/change-password", json=body, headers=temp)
        return response.status_code

    # Until the vendor picks a login ID, nothing else works
    assert client.get("/api/vendors/me", headers=temp).status_code == 403
    assert setup() == 400  # a password alone is not enough the first time
    assert setup(new_student_id="taken01") == 409
    assert setup(new_student_id="no spaces") == 422
    assert setup(new_student_id="currychef") == 200

    # The temporary login ID is gone; the chosen one signs in
    old = {"student_id": "curry01", "password": "curry-pass-789"}
    assert client.post("/api/auth/login", json=old).status_code == 401
    login = client.post(
        "/api/auth/login",
        json={"student_id": "currychef", "password": "curry-pass-789"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["must_choose_username"] is False
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # From now on the login ID is fixed; the password can still change
    renamed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "curry-pass-789",
            "new_password": "curry-pass-000",
            "new_student_id": "curryking",
        },
        headers=headers,
    )
    assert renamed.status_code == 400
    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "curry-pass-789", "new_password": "curry-pass-000"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["student_id"] == "currychef"


def test_customers_cannot_change_their_login_id(client: TestClient) -> None:
    alice = {
        "student_id": "990000001",
        "email": "alice@example.com",
        "phone_number": "0912345678",
        "password": "correct-horse-battery",
    }
    assert sign_up(client, alice).status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"student_id": alice["student_id"], "password": alice["password"]},
    ).json()
    assert login["user"]["must_choose_username"] is False
    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": alice["password"],
            "new_password": "brand-new-password-42",
            "new_student_id": "alice",
        },
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 400
