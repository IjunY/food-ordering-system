from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.auth.models import User
from app.auth.security import create_access_token
from app.core.config import Settings

ALICE = {
    "student_id": "112012345",
    "email": "alice@example.com",
    "phone_number": "0912345678",
    "password": "correct-horse-battery",
}


def register(client: TestClient, **overrides: str) -> dict:
    response = client.post("/api/auth/register", json={**ALICE, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, student_id: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", json={"student_id": student_id, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


# ---------- register ----------
def test_register_creates_a_customer(client: TestClient) -> None:
    user = register(client)

    assert user["student_id"] == ALICE["student_id"]
    assert user["email"] == ALICE["email"]
    assert user["phone_number"] == ALICE["phone_number"]
    assert user["role"] == "customer"
    assert "password" not in user
    assert "password_hash" not in user


def test_password_is_stored_hashed(client: TestClient) -> None:
    register(client)

    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        user = session.scalar(
            select(User).where(User.student_id == ALICE["student_id"])
        )
    assert user is not None
    assert user.password_hash != ALICE["password"]
    assert user.password_hash.startswith("$argon2")


def test_register_rejects_duplicate_student_id(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/api/auth/register", json={**ALICE, "email": "someone-else@example.com"}
    )
    assert response.status_code == 409
    assert "student ID" in response.json()["detail"]


def test_register_rejects_duplicate_email_ignoring_case(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/api/auth/register",
        json={**ALICE, "student_id": "112099999", "email": "Alice@Example.com"},
    )
    assert response.status_code == 409
    assert "email" in response.json()["detail"]


def test_register_validates_input(client: TestClient) -> None:
    bad_inputs = [
        {"password": "short"},
        {"email": "not-an-email"},
        {"phone_number": "abc"},
        {"student_id": "has spaces"},
    ]
    for bad in bad_inputs:
        response = client.post("/api/auth/register", json={**ALICE, **bad})
        assert response.status_code == 422, bad


# ---------- login ----------
def test_login_returns_token_and_user(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/api/auth/login",
        json={"student_id": ALICE["student_id"], "password": ALICE["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["student_id"] == ALICE["student_id"]


def test_login_rejects_wrong_password_and_unknown_user(client: TestClient) -> None:
    register(client)

    wrong_password = client.post(
        "/api/auth/login",
        json={"student_id": ALICE["student_id"], "password": "wrong-password"},
    )
    unknown_user = client.post(
        "/api/auth/login",
        json={"student_id": "000000000", "password": ALICE["password"]},
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    # Same answer for both, so it does not reveal which student IDs are registered
    assert wrong_password.json() == unknown_user.json()


# ---------- me ----------
def test_me_returns_the_signed_in_user(client: TestClient) -> None:
    register(client)
    token = login(client, ALICE["student_id"], ALICE["password"])

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["student_id"] == ALICE["student_id"]


def test_me_requires_a_valid_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401

    garbage = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert garbage.status_code == 401


def test_me_rejects_expired_token(client: TestClient, settings: Settings) -> None:
    user = register(client)
    expired = create_access_token(
        user["id"], settings.model_copy(update={"access_token_expire_minutes": -1})
    )

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


def test_token_signed_with_another_secret_is_rejected(
    client: TestClient, settings: Settings
) -> None:
    user = register(client)
    forged = create_access_token(
        user["id"],
        settings.model_copy(
            update={"jwt_secret": SecretStr("a-different-secret-0123456789-abcdefghij")}
        ),
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
