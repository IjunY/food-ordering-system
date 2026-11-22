from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "test", "loadtest", "prod"] = "dev"
    database_url: SecretStr  # Comes from explicit settings in test environment or .env during real deployment

    # Signs the login tokens (HS256). No default on purpose: a guessable secret lets anyone forge a login.
    jwt_secret: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = 60 * 24

    # Where uploaded photos are saved (served at /uploads/...). Relative paths are
    # relative to the folder the app is started from; in Docker this is a volume.
    upload_dir: Path = Path("uploads")

    # The address people open the app at. Links in emails (password reset) point
    # here; it is not taken from the request, so a forged Host header cannot send
    # a reset link to someone else's site. For a demo over the local network, set
    # it to that address, e.g. http://192.168.1.23:8000
    app_url: str = "http://localhost:8000"
    # How long a password reset link works
    password_reset_minutes: int = Field(default=30, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
