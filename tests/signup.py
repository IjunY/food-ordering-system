"""Signing up through the API the way the app does: first ask for the emailed
code, then register with it."""

import re
from typing import Any

import httpx2
from fastapi.testclient import TestClient

from app.mail.sender import Email, get_mailer

CODE = re.compile(r"\b([0-9]{6})\b")


class _Catch:
    def __init__(self) -> None:
        self.sent: list[Email] = []

    def send(self, email: Email) -> None:
        self.sent.append(email)


def sign_up(client: TestClient, body: dict[str, Any]) -> httpx2.Response:
    """Returns the response of the step that failed, or of the registration."""
    overrides = client.app.dependency_overrides  # type: ignore[attr-defined]
    previous = overrides.get(get_mailer)  # e.g. a test's own outbox
    catch = _Catch()
    overrides[get_mailer] = lambda: catch
    try:
        sent = client.post(
            "/api/auth/register/send-code", json={"email": body.get("email")}
        )
    finally:
        if previous is None:
            overrides.pop(get_mailer, None)
        else:
            overrides[get_mailer] = previous
    if sent.status_code != 202:
        return sent
    match = CODE.search(catch.sent[-1].body)
    assert match is not None, catch.sent[-1].body
    return client.post("/api/auth/register", json={**body, "email_code": match[1]})
