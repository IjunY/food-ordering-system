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

## Database and data

Apply the migrations, then load the NTHU campus vendors and menus plus the demo
accounts (`112012345` customer, `staff` for 牛肉先生, `admin`):

```bash
uv run alembic upgrade head
uv run python scripts/seed_demo.py --password <password for the demo accounts>
```

With Docker, run the same commands inside the app container, e.g.
`docker compose exec app alembic upgrade head`.

- The migrations also upgrade a database that already has menu items and
  orders: no need to wipe it (`docker compose down -v`) first.
- The vendors and menus are in `scripts/nthu_menu.json` (real stalls in Fengyun
  Hall, Shuimu Center and the Snack Bar; its `_comment` says where the data came
  from). Running the seed again updates existing vendors and items to match the
  file. Add `--close-others` to stop older vendors that are not in the file
  (such as the earlier sample vendors) from taking orders; nothing is deleted.
- Staff accounts belong to one vendor (`users.vendor_id`) and only see and change
  that vendor's orders, menu and "accepting orders" switch
  (`PATCH /api/vendors/{id}`). Platform admins can see every vendor's orders but
  not change them. The seed links the demo `staff` account to 牛肉先生.
- A vendor that is not accepting orders (`is_accepting_orders = false`) cannot
  receive new orders (409).
