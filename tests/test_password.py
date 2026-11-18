import httpx2
import jwt
from fastapi.testclient import TestClient

from app.core.config import Settings

ALICE = {
    "student_id": "990000001",
    "email": "alice@example.com",
    "phone_number": "0912345678",
    "password": "correct-horse-battery",
}
NEW_PASSWORD = "brand-new-password-42"


def sign_in(client: TestClient, password: str = ALICE["password"]) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"student_id": ALICE["student_id"], "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def change(
    client: TestClient, headers: dict[str, str], current: str, new: str
) -> httpx2.Response:
    return client.post(
        "/api/auth/change-password",
        json={"current_password": current, "new_password": new},
        headers=headers,
    )


def test_user_changes_their_password(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=ALICE).status_code == 201
    this_session = sign_in(client)
    other_session = sign_in(client)  # e.g. the same account on another phone

    response = change(client, this_session, ALICE["password"], NEW_PASSWORD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["student_id"] == ALICE["student_id"]
    fresh = {"Authorization": f"Bearer {body['access_token']}"}

    # Every token from before the change stops working, on every device ...
    assert client.get("/api/auth/me", headers=this_session).status_code == 401
    assert client.get("/api/auth/me", headers=other_session).status_code == 401
    # ... while the one handed back keeps this session going
    assert client.get("/api/auth/me", headers=fresh).status_code == 200
    assert client.get("/api/orders", headers=fresh).status_code == 200

    # Only the new password signs in now
    old_login = client.post(
        "/api/auth/login",
        json={"student_id": ALICE["student_id"], "password": ALICE["password"]},
    )
    assert old_login.status_code == 401
    sign_in(client, NEW_PASSWORD)


def test_change_password_rules(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=ALICE).status_code == 201
    headers = sign_in(client)

    # Must be signed in
    no_login = client.post(
        "/api/auth/change-password",
        json={"current_password": ALICE["password"], "new_password": NEW_PASSWORD},
    )
    assert no_login.status_code == 401
    # Wrong current password: 400, not 401, so the frontend does not sign the user out
    assert change(client, headers, "not-my-password", NEW_PASSWORD).status_code == 400
    # Same as the current one
    assert (
        change(client, headers, ALICE["password"], ALICE["password"]).status_code == 400
    )
    # Same length rules as sign-up
    assert change(client, headers, ALICE["password"], "short").status_code == 422
    assert change(client, headers, ALICE["password"], "x" * 129).status_code == 422

    # None of the failed attempts changed anything, and the token still works
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    sign_in(client)


def test_tokens_without_a_version_are_rejected(
    client: TestClient, settings: Settings
) -> None:
    """Tokens issued before this change have no "ver" claim; they must not slip
    past the check that a password change relies on."""
    user = client.post("/api/auth/register", json=ALICE).json()
    legacy = jwt.encode(
        {"sub": str(user["id"]), "exp": 9_999_999_999},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy}"})
    assert response.status_code == 401


def test_self_registered_accounts_are_not_forced_to_change(
    client: TestClient,
) -> None:
    user = client.post("/api/auth/register", json=ALICE).json()
    assert user["must_change_password"] is False
    assert client.get("/api/orders", headers=sign_in(client)).status_code == 200
