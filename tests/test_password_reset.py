"""Forgot password: a one-time link by email, then a new password."""

import logging
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from fastapi.testclient import TestClient
from signup import sign_up

from app.auth.service import request_password_reset
from app.auth.states import UserRole
from app.core.config import Settings
from app.mail.config import MailSettings
from app.mail.sender import Email, LogMailer, SmtpMailer, get_mailer

ALICE = {
    "student_id": "990000001",
    "email": "alice@example.com",
    "phone_number": "0912345678",
    "password": "correct-horse-battery",
}
NEW_PASSWORD = "brand-new-password-42"
LINK = re.compile(r"(\S+)#reset-([0-9a-f]{64})")


class Outbox:
    def __init__(self) -> None:
        self.sent: list[Email] = []

    def send(self, email: Email) -> None:
        self.sent.append(email)

    def tokens(self) -> list[str]:
        return [m.group(2) for e in self.sent for m in [LINK.search(e.body)] if m]


@pytest.fixture
def outbox(client: TestClient) -> Iterator[Outbox]:
    box = Outbox()
    client.app.dependency_overrides[get_mailer] = lambda: box  # type: ignore[attr-defined]
    yield box
    client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
def alice(client: TestClient) -> None:
    assert sign_up(client, ALICE).status_code == 201


def sign_in(client: TestClient, student_id: str, password: str) -> httpx2.Response:
    return client.post(
        "/api/auth/login", json={"student_id": student_id, "password": password}
    )


def forgot(client: TestClient, account: str) -> httpx2.Response:
    return client.post("/api/auth/forgot-password", json={"account": account})


def reset(client: TestClient, token: str, password: str = NEW_PASSWORD):
    return client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": password}
    )


def make_link(client: TestClient, account: str, now: datetime) -> str:
    """A link made at another time than now (for expiry and the one-per-minute rule)."""
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        found = request_password_reset(session, account, timedelta(minutes=30), now)
    assert found is not None
    return found[1]


def test_forgotten_password_is_reset_from_the_emailed_link(
    client: TestClient, settings: Settings, outbox: Outbox, alice: None
) -> None:
    old_login = sign_in(client, ALICE["student_id"], ALICE["password"]).json()
    old = {"Authorization": f"Bearer {old_login['access_token']}"}

    assert forgot(client, ALICE["student_id"]).status_code == 202
    [email] = outbox.sent
    assert email.to == ALICE["email"]
    match = LINK.search(email.body)
    assert match is not None
    # The link points at the configured address, never at the request's Host
    assert match.group(1) == f"{settings.app_url}/"
    token = match.group(2)

    response = reset(client, token)
    assert response.status_code == 200, response.text
    assert response.json()["user"]["student_id"] == ALICE["student_id"]
    fresh = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/api/orders", headers=fresh).status_code == 200

    # Sessions from before are signed out; only the new password works
    assert client.get("/api/auth/me", headers=old).status_code == 401
    assert sign_in(client, ALICE["student_id"], ALICE["password"]).status_code == 401
    assert sign_in(client, ALICE["student_id"], NEW_PASSWORD).status_code == 200

    # The link works once
    assert reset(client, token, "yet-another-password").status_code == 400


def test_the_answer_does_not_reveal_which_accounts_exist(
    client: TestClient, outbox: Outbox, alice: None
) -> None:
    unknown_id = forgot(client, "nobody99")
    unknown_email = forgot(client, "nobody@example.com")
    assert outbox.sent == []

    by_email = forgot(client, "  ALICE@Example.com ")  # any case, spaces trimmed
    assert [e.to for e in outbox.sent] == [ALICE["email"]]
    for response in (unknown_id, unknown_email):
        assert response.status_code == by_email.status_code == 202
        assert response.content == by_email.content


def test_one_email_per_minute(client: TestClient, outbox: Outbox, alice: None) -> None:
    assert forgot(client, ALICE["student_id"]).status_code == 202
    assert forgot(client, ALICE["student_id"]).status_code == 202
    assert len(outbox.sent) == 1  # the second request sent nothing
    # A minute later another link can be sent
    later = datetime.now(UTC) + timedelta(minutes=2)
    assert make_link(client, ALICE["student_id"], later)


def test_expired_links_do_not_work(client: TestClient, alice: None) -> None:
    token = make_link(
        client, ALICE["student_id"], datetime.now(UTC) - timedelta(minutes=31)
    )
    assert reset(client, token).status_code == 400
    assert sign_in(client, ALICE["student_id"], ALICE["password"]).status_code == 200


def test_a_new_password_closes_every_open_link(
    client: TestClient, outbox: Outbox, alice: None
) -> None:
    earlier = make_link(
        client, ALICE["student_id"], datetime.now(UTC) - timedelta(minutes=5)
    )
    forgot(client, ALICE["student_id"])
    [latest] = outbox.tokens()
    assert reset(client, latest).status_code == 200
    assert reset(client, earlier, "yet-another-password").status_code == 400

    # Changing the password while signed in closes open links too
    link = make_link(
        client, ALICE["student_id"], datetime.now(UTC) + timedelta(minutes=2)
    )
    signed_in = sign_in(client, ALICE["student_id"], NEW_PASSWORD).json()
    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": NEW_PASSWORD, "new_password": "changed-on-purpose"},
        headers={"Authorization": f"Bearer {signed_in['access_token']}"},
    )
    assert changed.status_code == 200
    assert reset(client, link, "attacker-password").status_code == 400


def test_reset_input_is_checked(
    client: TestClient, outbox: Outbox, alice: None
) -> None:
    assert reset(client, "not-a-token").status_code == 422
    assert reset(client, "0" * 64).status_code == 400  # well-formed but unknown
    forgot(client, ALICE["student_id"])
    [token] = outbox.tokens()
    assert reset(client, token, "short").status_code == 422  # same rules as sign-up
    assert forgot(client, "").status_code == 422


def test_a_vendor_still_picks_a_login_id_after_a_reset(
    client: TestClient, outbox: Outbox, auth_headers: Callable[..., dict[str, str]]
) -> None:
    admin = auth_headers("admin01", UserRole.ADMIN)
    staff = {
        "student_id": "temp0001",
        "email": "vendor@example.com",
        "phone_number": "0912345678",
        "password": "first-password-123",
    }
    assert client.post("/api/admin/staff", json=staff, headers=admin).status_code == 201

    # Forgot the temporary password before ever signing in
    forgot(client, "vendor@example.com")
    [token] = outbox.tokens()
    user = reset(client, token).json()["user"]
    assert user["must_change_password"] is False
    assert user["must_choose_username"] is True  # the login ID is still the admin's


def test_a_mail_server_that_is_down_does_not_break_the_form(
    client: TestClient, alice: None
) -> None:
    class Broken:
        def send(self, email: Email) -> None:
            raise ConnectionRefusedError("smtp down")

    client.app.dependency_overrides[get_mailer] = lambda: Broken()  # type: ignore[attr-defined]
    try:
        assert forgot(client, ALICE["student_id"]).status_code == 202
    finally:
        client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


def test_without_smtp_the_link_is_only_logged_in_development(
    caplog: pytest.LogCaptureFixture,
) -> None:
    email = Email(to="a@example.com", subject="Reset", body="#reset-" + "a" * 64)
    with caplog.at_level(logging.WARNING, logger="app.mail.sender"):
        LogMailer(show_body=True).send(email)
        assert "#reset-" in caplog.text
        caplog.clear()
        LogMailer(show_body=False).send(email)  # production: never log the link
        assert "a@example.com" in caplog.text and "#reset-" not in caplog.text


def test_smtp_is_used_once_a_host_is_set(client: TestClient) -> None:
    app = client.app

    class FakeRequest:
        def __init__(self) -> None:
            self.app = app

    request = FakeRequest()
    with_smtp = MailSettings(smtp_host="smtp.example.com", _env_file=None)  # pyright: ignore[reportCallIssue]
    without = MailSettings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert isinstance(get_mailer(request, with_smtp), SmtpMailer)  # type: ignore[arg-type]
    assert isinstance(get_mailer(request, without), LogMailer)  # type: ignore[arg-type]
