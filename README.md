# Food Ordering System
## NTHU I2PI Final Project

## Running

With Docker (app + Postgres; needs a `.env` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`):

```bash
docker compose up --build
```

Locally, without Docker (needs `DATABASE_URL` set, e.g. in `.env`):

```bash
uv run uvicorn app.main:create_app --factory --reload
```

`app/main.py` exposes an app factory (`create_app`), not a module-level `app`,
so point uvicorn at `app.main:create_app` (not `app.main:app`) and pass
`--factory` to say so explicitly. `tests/test_container_entrypoint.py` checks
that the Dockerfile's `CMD` stays in sync with this.
