from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
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

    # The admin knows this first password, so the account starts locked down
    assert staff["must_change_password"] is True

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
    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": NEW_STAFF["password"],
            "new_password": "my-own-password-456",
        },
        headers=first,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["user"]["must_change_password"] is False
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
