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


ENTRYPOINT_SCRIPT = DOCKERFILE.parent / "scripts" / "docker-entrypoint.sh"


def test_dockerfile_runs_the_entrypoint_script() -> None:
    lines = [
        line
        for line in DOCKERFILE.read_text().splitlines()
        if line.startswith("ENTRYPOINT ")
    ]
    assert len(lines) == 1, "expected exactly one ENTRYPOINT line in the Dockerfile"
    assert json.loads(lines[0].removeprefix("ENTRYPOINT ")) == [
        "sh",
        "/code/scripts/docker-entrypoint.sh",
    ]


def _start_container(tmp_path: Path, env: dict[str, str]) -> tuple[int, list[str]]:
    """Runs the entrypoint with stand-ins for alembic and python that log their arguments."""
    import os
    import subprocess

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "log"
    for name in ("alembic", "python"):
        fake = bin_dir / name
        fake.write_text(
            f'#!/bin/sh\necho "{name} $*" >> "{log}"\nexit "${{FAIL_{name.upper()}:-0}}"\n'
        )
        fake.chmod(0o755)
    result = subprocess.run(
        ["sh", str(ENTRYPOINT_SCRIPT), "sh", "-c", f'echo "app started" >> "{log}"'],
        env={"PATH": f"{bin_dir}:{os.environ['PATH']}", **env},
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, log.read_text().splitlines() if log.exists() else []


def test_container_start_migrates_then_seeds_then_starts_the_app(
    tmp_path: Path,
) -> None:
    code, steps = _start_container(tmp_path, {"DEMO_PASSWORD": "demo-password-123"})
    assert code == 0
    assert steps == [
        "alembic upgrade head",
        "python -m scripts.seed_demo --if-empty",
        "app started",
    ]


def test_without_demo_password_nothing_is_seeded(tmp_path: Path) -> None:
    code, steps = _start_container(tmp_path, {})
    assert code == 0
    assert steps == ["alembic upgrade head", "app started"]


def test_a_failed_migration_keeps_the_app_from_starting(tmp_path: Path) -> None:
    code, steps = _start_container(
        tmp_path, {"DEMO_PASSWORD": "demo-password-123", "FAIL_ALEMBIC": "1"}
    )
    assert code != 0
    assert steps == ["alembic upgrade head"]
