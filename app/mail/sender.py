"""Sending email. Routes depend on get_mailer; tests swap in a fake outbox."""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Annotated, Protocol

from fastapi import Depends, Request

from app.mail.config import MailSettings, get_mail_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str  # plain text


class Mailer(Protocol):
    def send(self, email: Email) -> None: ...


class SmtpMailer:
    def __init__(self, settings: MailSettings) -> None:
        self._settings = settings

    def send(self, email: Email) -> None:
        s = self._settings
        message = EmailMessage()
        message["From"] = s.sender or s.smtp_username
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)

        context = ssl.create_default_context()
        if s.smtp_port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                s.smtp_host, s.smtp_port, timeout=15, context=context
            )
        else:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15)
        with server:
            if s.smtp_port != 465:
                server.starttls(context=context)
            if s.smtp_username:
                server.login(s.smtp_username, s.smtp_password.get_secret_value())
            server.send_message(message)


class LogMailer:
    """No SMTP server set up: writes the email to the server log instead.

    Only in development. In production the body (which holds a working reset
    link) is left out, since whoever reads the logs could otherwise use it.
    """

    def __init__(self, show_body: bool) -> None:
        self._show_body = show_body

    def send(self, email: Email) -> None:
        if self._show_body:
            logger.warning(
                "Email not sent (MAIL_SMTP_HOST is not set). To: %s\nSubject: %s\n\n%s",
                email.to,
                email.subject,
                email.body,
            )
        else:
            logger.error(
                "Email to %s was not sent: set MAIL_SMTP_HOST to send email", email.to
            )


def get_mailer(
    request: Request,
    settings: Annotated[MailSettings, Depends(get_mail_settings)],
) -> Mailer:
    if settings.smtp_host:
        return SmtpMailer(settings)
    return LogMailer(show_body=request.app.state.app_settings.app_env != "prod")


def send_quietly(mailer: Mailer, email: Email) -> None:
    """For background tasks: a mail server that is down is logged, not raised."""
    try:
        mailer.send(email)
    except Exception:
        logger.exception("Could not send email to %s", email.to)
