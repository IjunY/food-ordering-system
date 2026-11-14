import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import sessionmaker

from app.auth.schemas import UserRegister
from app.auth.security import create_access_token
from app.auth.service import register_user
from app.auth.states import UserRole
from app.core.config import Settings
from app.main import create_app

# Same database the migrations ran on: CI sets DATABASE_URL, locally it is the
# docker-compose one. Run `uv run alembic upgrade head` first so the tables exist.
TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://meal:change-me@localhost:5433/meal"
)


# Initiating fake test settings
@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        jwt_secret=SecretStr("test-only-secret-not-used-anywhere-else-0123456789"),
        app_env="test",
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )


# Starting the fastapi test client
@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings=settings)
    engine = app.state.session_factory.kw["bind"]

    # Cleanup: everything a test writes happens inside one outer transaction that is
    # rolled back at the end, so tests never leave rows behind (even after a commit).
    with engine.connect() as connection:
        transaction = connection.begin()
        app.state.session_factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        with TestClient(app) as test_client:
            # Give the test_client to the test, comes back after the test
            yield test_client
        transaction.rollback()
    engine.dispose()


# Creates an account with the given role and returns the headers that sign it in.
# Registration only makes customers, so staff/admin accounts are created here directly.
@pytest.fixture
def auth_headers(
    client: TestClient, settings: Settings
) -> Callable[..., dict[str, str]]:
    def make(
        student_id: str = "112012345", role: UserRole = UserRole.CUSTOMER
    ) -> dict[str, str]:
        with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
            user = register_user(
                session,
                UserRegister(
                    student_id=student_id,
                    email=f"{student_id}@example.com",
                    phone_number="0912345678",
                    password="correct-horse-battery",
                ),
                role=role,
            )
        return {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}

    return make
