# syntax=docker/dockerfile:1

# ---------- Stage 1: build the virtualenv ----------
FROM python:3.12-slim AS builder

# Pin uv to the exact version you run locally (`uv --version`)
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /code

# Dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Our code
COPY . /code
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- Stage 2: runtime image ----------
FROM python:3.12-slim

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=builder /code /code
ENV PATH="/code/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /code
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]