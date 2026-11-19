# Food Ordering System
## NTHU I2PI Final Project

## Running

With Docker (app + Postgres; needs a `.env` like `.env.example`, including
`JWT_SECRET` and `PAYMENT_WEBHOOK_SECRET`, or Compose will not start even the database):

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
- The app shows vendors, menus, add-ons and orders from the database only.
  `frontend/js/mock/data.js` is a separate copy used for the first-login
  tutorial (practice orders never reach the database) and for opening the
  frontend without a backend.
- Each vendor has an `area` (`fengyun`, `shuimu`, `snack` or `other`; the home
  page tabs) and a `cover_image_url`. Each menu item has a description,
  `prep_minutes` and `option_groups` (add-ons such as rice amount or toppings).
  Orders keep the add-ons and note the customer picked, and the price includes
  the add-ons.
- Photos uploaded in the app (`POST /api/uploads`, staff and admins) are saved
  in `uploads/` (a Docker volume) and served at `/uploads/...`.

## Demo: opening a new vendor

1. Sign in as `admin` → 餐廳管理 → 新增店家. Enter the store (names, area,
   location) and its login (ID, first password, email, phone).
2. Sign out, sign in with that login. The vendor is asked to set its own
   password first, then lands on its order board (with a short tutorial that
   uses practice orders).
3. 菜單管理 → 新增品項: names, category, price, prep time, description and
   photo, in Chinese and English. The item appears on the customer side right
   away; 店家設定 changes the store details and photos.

## Payments

The pay button goes through the backend's payments module (`app/payments`).
`PAYMENT_PROVIDER` in `.env` picks the provider:

- `mock` (default): the backend's own checkout page with "success / fail"
  buttons. No account needed.
- `linepay`: the LINE Pay **sandbox** (no real money).
  1. Create a sandbox channel at
     https://pay.line.me/tw/developers/techsupport/sandbox/creation; LINE Pay
     emails a Channel ID and Channel Secret.
  2. In `.env`: `PAYMENT_PROVIDER=linepay`, `PAYMENT_LINEPAY_CHANNEL_ID=...`,
     `PAYMENT_LINEPAY_CHANNEL_SECRET=...`, then restart the app
     (`docker compose up --build`).
  3. Pay with "LINE Pay": the browser goes to LINE Pay's sandbox page, and
     after approving it comes back to `/api/payments/linepay/confirm`, where
     the server asks LINE Pay to confirm the charge and then shows the pickup
     pass. Works on localhost: LINE Pay only redirects the browser, it does not
     call our server.

"Pay at pickup" marks the order (`POST /api/orders/{id}/pay-at-pickup`) instead.
The vendor's board has four columns: unpaid (pay at counter), paid (not
accepted yet), accepted (preparing) and ready. Orders that are neither paid
nor marked pay-at-pickup stay off the board.

## Looking at the database

The database runs in the `db` container (Postgres, user/database from `.env`).

- From the terminal:
  `docker compose exec db psql -U meal -d meal`, then e.g. `\dt` (tables),
  `select id, name_zh, area from vendors;`, `\q` to quit.
- With a GUI (TablePlus, DBeaver, pgAdmin, or the VS Code PostgreSQL
  extension): host `localhost`, port `5433`, user and database `meal`, and the
  `POSTGRES_PASSWORD` from `.env`.
- Through the API: http://127.0.0.1:8000/docs lists every endpoint and can
  call them.
