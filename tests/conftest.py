from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


# Initiating fake test settings
@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=SecretStr("postgresql://meal:change-me@localhost:5432/meal_test"),
        app_env="test",
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )


# Starting the fastapi test client
@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings=settings)
    with TestClient(app) as test_client:
        # Give the test_client to the test, comes back after the test
        yield test_client

    # TODO: cleanup work
