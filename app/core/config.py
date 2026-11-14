from functools import lru_cache
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


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
