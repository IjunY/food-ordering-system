"""Signing up needs the 6-digit code emailed to the address."""

import smtplib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any, Self

import httpx2
import pytest
from fastapi.testclient import TestClient
from signup import CODE
from sqlalchemy.orm import Session

from app.auth.schemas import UserSignUp
from app.auth.service import (
    CODE_VALID_FOR,
    MAX_CODE_ATTEMPTS,
    send_signup_code,
    sign_up,
)
from app.core.errors import BadRequestError, TooManyRequestsError
from app.mail.config import MailSettings
from app.mail.sender import Email, SmtpMailer, get_mailer

ALICE = {
    "student_id": "990000001",
    "email": "alice@example.com",
    "phone_number": "0912345678",
    "password": "correct-horse-battery",
}


class Outbox:
    def __init__(self) -> None:
        self.sent: list[Email] = []

    def send(self, email: Email) -> None:
        self.sent.append(email)

    def last_code(self) -> str:
        match = CODE.search(self.sent[-1].body)
        assert match is not None
        return match[1]


@pytest.fixture
def outbox(client: TestClient) -> Iterator[Outbox]:
    box = Outbox()
    client.app.dependency_overrides[get_mailer] = lambda: box  # type: ignore[attr-defined]
    yield box
    client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
def session(client: TestClient) -> Iterator[Session]:
    with client.app.state.session_factory() as s:  # type: ignore[attr-defined]
        yield s


def send_code(client: TestClient, email: str) -> httpx2.Response:
    return client.post("/api/auth/register/send-code", json={"email": email})


def register(client: TestClient, code: str, **overrides: Any) -> httpx2.Response:
    return client.post(
        "/api/auth/register", json={**ALICE, "email_code": code, **overrides}
    )


def test_sign_up_with_the_emailed_code(client: TestClient, outbox: Outbox) -> None:
    assert send_code(client, ALICE["email"]).status_code == 202

    [email] = outbox.sent
    assert email.to == ALICE["email"]
    assert "感謝您註冊 NTHU 點餐系統，以下是您的驗證碼：" in email.body
    code = outbox.last_code()
    # In the HTML version the code sits on its own line, large and bold
    assert email.html is not None
    assert "font-size:36px;font-weight:700" in email.html
    assert f">{code}</p>" in email.html

    response = register(client, code)
    assert response.status_code == 201, response.text
    assert response.json()["email"] == ALICE["email"]
    login = client.post(
        "/api/auth/login",
        json={"student_id": ALICE["student_id"], "password": ALICE["password"]},
    )
    assert login.status_code == 200


def test_no_account_without_the_right_code(client: TestClient, outbox: Outbox) -> None:
    # Without a code: the request is incomplete
    assert client.post("/api/auth/register", json=ALICE).status_code == 422
    assert register(client, "12345").status_code == 422  # not 6 digits
    # No code was ever sent to this address
    assert register(client, "123456").status_code == 400

    send_code(client, ALICE["email"])
    code = outbox.last_code()
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"
    response = register(client, wrong)
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"]

    # A code proves one address only
    other = register(client, code, email="bob@example.com")
    assert other.status_code == 400

    assert register(client, code).status_code == 201
    # Used once: it does not work again (e.g. for a second account)
    again = register(client, code, student_id="990000002")
    assert again.status_code == 400


def test_email_case_does_not_matter(client: TestClient, outbox: Outbox) -> None:
    send_code(client, "Alice@Example.com")
    assert outbox.sent[-1].to == "alice@example.com"
    assert register(client, outbox.last_code()).status_code == 201


def test_no_code_for_an_address_that_already_has_an_account(
    client: TestClient, outbox: Outbox
) -> None:
    send_code(client, ALICE["email"])
    register(client, outbox.last_code())

    response = send_code(client, "ALICE@example.com")
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]
    assert len(outbox.sent) == 1
    assert send_code(client, "not-an-email").status_code == 422


def test_one_code_email_per_minute(client: TestClient, outbox: Outbox) -> None:
    assert send_code(client, ALICE["email"]).status_code == 202
    assert send_code(client, ALICE["email"]).status_code == 429
    assert len(outbox.sent) == 1
    # Other addresses are not held up
    assert send_code(client, "bob@example.com").status_code == 202


def _signup(**overrides: Any) -> UserSignUp:
    return UserSignUp.model_validate({**ALICE, **overrides})


def test_a_new_code_replaces_the_old_one(session: Session) -> None:
    now = datetime.now(UTC)
    first = send_signup_code(session, ALICE["email"], now)
    later = now + timedelta(minutes=2)
    second = send_signup_code(session, ALICE["email"], later)
    with pytest.raises(TooManyRequestsError):
        send_signup_code(session, ALICE["email"], later + timedelta(seconds=30))

    if first != second:
        with pytest.raises(BadRequestError):
            sign_up(session, _signup(email_code=first), later)
    assert sign_up(session, _signup(email_code=second), later).email == ALICE["email"]


def test_codes_expire(session: Session) -> None:
    now = datetime.now(UTC)
    code = send_signup_code(session, ALICE["email"], now)
    with pytest.raises(BadRequestError, match="expired"):
        sign_up(session, _signup(email_code=code), now + CODE_VALID_FOR)
    assert sign_up(
        session, _signup(email_code=code), now + CODE_VALID_FOR - timedelta(seconds=1)
    )


def test_too_many_wrong_codes_close_the_code(session: Session) -> None:
    now = datetime.now(UTC)
    code = send_signup_code(session, ALICE["email"], now)
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"
    for _ in range(MAX_CODE_ATTEMPTS):
        with pytest.raises(BadRequestError, match="incorrect"):
            sign_up(session, _signup(email_code=wrong), now)
    # Even the right code no longer works: a new one has to be sent
    with pytest.raises(BadRequestError, match="expired"):
        sign_up(session, _signup(email_code=code), now)


def test_a_taken_student_id_does_not_use_up_the_code(
    client: TestClient, outbox: Outbox
) -> None:
    send_code(client, ALICE["email"])
    register(client, outbox.last_code())
    send_code(client, "bob@example.com")
    code = outbox.last_code()

    taken = register(client, code, email="bob@example.com")  # Alice's student ID
    assert taken.status_code == 409
    # Bob picks another student ID and the same code still works
    response = register(client, code, email="bob@example.com", student_id="990000002")
    assert response.status_code == 201


def test_smtp_sends_the_html_version_too(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[EmailMessage] = []

    class FakeSmtp:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def starttls(self, **kwargs: object) -> None:
            pass

        def login(self, *args: object) -> None:
            pass

        def send_message(self, message: EmailMessage) -> None:
            sent.append(message)

    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    settings = MailSettings(smtp_host="smtp.example.com", _env_file=None)  # pyright: ignore[reportCallIssue]
    SmtpMailer(settings).send(
        Email(
            to="a@example.com", subject="s", body="plain 123456", html="<b>123456</b>"
        )
    )
    [message] = sent
    assert message.is_multipart()
    parts = {
        part.get_content_type(): part.get_content()
        for part in message.walk()
        if not part.is_multipart()
    }
    assert "plain 123456" in parts["text/plain"]
    assert "<b>123456</b>" in parts["text/html"]
