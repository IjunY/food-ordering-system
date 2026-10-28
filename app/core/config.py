from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "test", "loadtest", "prod"] = "dev"
    database_url: SecretStr  # no default: the app refuses to start without it


@lru_cache
def get_settings() -> Settings:
    return Settings()
