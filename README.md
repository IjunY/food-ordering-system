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

### Menu (`app/menu`)

| Method | Path | Who | What |
|---|---|---|---|
| GET | `/api/vendors` | anyone | Names of the vendors that have menu items |
| GET | `/api/menu-items` | anyone | The menu. Optional `?vendor=...` and `?available_only=true` |
| GET | `/api/menu-items/{id}` | anyone | One item |
| POST | `/api/menu-items` | staff / admin | Add an item: `vendor`, `item_name`, `price`, `is_available` |
| PATCH | `/api/menu-items/{id}` | staff / admin | Change only the fields that are sent |
| DELETE | `/api/menu-items/{id}` | staff / admin | Remove an item. `409` if an order already uses it; set `is_available` to `false` instead |

### Orders (`app/orders`)

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/orders` | signed in | Place an order: `{"items": [{"item_id": 1, "quantity": 2}]}` |
| GET | `/api/orders` | signed in | Customers get their own orders; staff get everyone's (`?mine=true` for their own). Optional `?status=`, `?limit=`, `?offset=` |
| GET | `/api/orders/{id}` | owner or staff | One order with its items and total |
| PATCH | `/api/orders/{id}/status` | staff / admin | Move the order on: `{"status": "preparing"}` |
| POST | `/api/orders/{id}/cancel` | owner or staff | Customers can cancel only while the order is `confirming` |

- An order can only contain items from one vendor, and only items that are available.
- Prices come from the menu at the moment of ordering (`unit_price`); later menu changes do not affect existing orders.
- `orders.created_by` holds the customer's `student_id`.
- Status flow: `confirming` -> `preparing` -> `ready` -> `picked up`. `cancelled` is possible any time before pick-up.
  The table lives in `ALLOWED_TRANSITIONS` (`app/orders/states.py`).

