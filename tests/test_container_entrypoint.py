"""Guard against the Dockerfile CMD drifting away from app/main.py.

The app is built through a factory (`create_app`) with no module-level `app`,
so the container must start uvicorn with `app.main:create_app --factory`.
This test reads the real CMD from the Dockerfile and asks uvicorn to load it
exactly the way the container would, so a mismatch fails CI instead of
failing at `docker compose up`.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI

from app.core.config import get_settings

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def _dockerfile_cmd() -> list[str]:
    cmd_lines = [
        line for line in DOCKERFILE.read_text().splitlines() if line.startswith("CMD ")
    ]
    assert len(cmd_lines) == 1, "expected exactly one CMD line in the Dockerfile"
    cmd = json.loads(cmd_lines[0].removeprefix("CMD "))
    assert isinstance(cmd, list), "CMD should use exec (JSON array) form"
    return [str(part) for part in cmd]


@pytest.fixture
def container_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # docker-compose injects DATABASE_URL; mimic that without touching a real DB.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_dockerfile_cmd_loads_the_app(container_env: None) -> None:
    cmd = _dockerfile_cmd()
    assert cmd[0] == "uvicorn"

    target = cmd[1]
    config = uvicorn.Config(target, factory="--factory" in cmd)
    config.load()  # raises SystemExit if the target can't be imported/called

    # uvicorn wraps the app in its own middleware; unwrap down to the real app.
    # This also catches `create_app` without `--factory`, which uvicorn would
    # load "successfully" as a plain callable instead of calling it.
    loaded = config.loaded_app
    while not isinstance(loaded, FastAPI) and hasattr(loaded, "app"):
        loaded = loaded.app
    assert isinstance(loaded, FastAPI), f"{target!r} did not produce a FastAPI app"
