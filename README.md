# Food Ordering System
## NTHU I2PI Final Project

## Running locally

```bash
cp .env.example .env          # then change POSTGRES_PASSWORD and JWT_SECRET
docker compose up -d db       # Postgres on localhost:5433
uv sync
uv run alembic upgrade head   # create / update the tables
uv run uvicorn app.main:create_app --factory --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

Tests run against the database in `DATABASE_URL` (default: the docker-compose one) and
need the tables to exist, so run `uv run alembic upgrade head` first. Each test runs
inside a transaction that is rolled back, so nothing is left behind.

```bash
uv run pytest -q
```

## API

Every endpoint is under `/api`. Errors come back as `{"detail": "..."}`.

### Auth (`app/auth`)

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/auth/register` | anyone | Create an account: `student_id`, `email`, `phone_number`, `password` (8+ characters) |
| POST | `/api/auth/login` | anyone | `student_id` + `password` -> `{access_token, token_type, user}` |
| GET | `/api/auth/me` | signed in | The current user |

Send the token on later requests as `Authorization: Bearer <access_token>` (valid for 24 hours).

- Passwords are stored as Argon2 hashes, never in plain text.
- `users.role` is `customer` (what registration creates), `staff` or `admin`.
  Other modules can protect endpoints with `CurrentUser` / `StaffUser` from `app/auth/dependencies.py`.
