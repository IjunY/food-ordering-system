"""Settings for sending email (password reset links), read from MAIL_* variables.

Without MAIL_SMTP_HOST nothing is sent: in development the email is written to
the server log instead (docker compose logs app), so the flow can still be tried.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MailSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="MAIL_", extra="ignore"
    )

    # e.g. smtp.gmail.com; empty = do not send, log instead (development only)
    smtp_host: str = ""
    # 587 with STARTTLS (the usual); 465 means TLS from the start
    smtp_port: int = Field(default=587, gt=0, lt=65536)
    smtp_username: str = ""
    # For Gmail: an app password (Google Account > Security > App passwords),
    # not the account's normal password
    smtp_password: SecretStr = SecretStr("")
    # The From address; defaults to the SMTP username
    sender: str = ""


@lru_cache
def get_mail_settings() -> MailSettings:
    return MailSettings()
