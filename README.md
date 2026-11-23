# Food Ordering System
## NTHU I2PI Final Project

## Running

With Docker (app + Postgres), one command:

```bash
docker compose up --build
```

Then open http://localhost:8000. Every time the app container starts, it first
brings the database up to date (`alembic upgrade head`). On the very first start,
if `DEMO_PASSWORD` is set in `.env`, it also loads the NTHU stalls and menus and
the demo accounts (see below) with that password. Later starts leave the data
alone, so whatever was changed in the app survives a restart. If a step fails,
the app does not start and `docker compose logs app` says why.

It needs a `.env` (Compose will not start even the database without
`POSTGRES_PASSWORD`, `JWT_SECRET` and `PAYMENT_WEBHOOK_SECRET`). On a fresh
clone, create one from the template and fill in the values:

```bash
cp -n .env.example .env   # -n: never overwrites an existing .env
```

`.env` holds your own secrets and is never committed; `.env.example` only lists
the settings with placeholder values.

Locally, without Docker (needs `DATABASE_URL` set, e.g. in `.env`):

```bash
uv run uvicorn app.main:create_app --factory --reload
```

`app/main.py` exposes an app factory (`create_app`), not a module-level `app`,
so point uvicorn at `app.main:create_app` (not `app.main:app`) and pass
`--factory` to say so explicitly. `tests/test_container_entrypoint.py` checks
that the Dockerfile's `CMD` stays in sync with this.

## Database and data

With Docker this happens by itself (see Running). Without Docker, apply the
migrations, then load the NTHU campus vendors and menus plus the demo accounts
(`112012345` customer, `staff` for 牛肉先生, `admin`):

```bash
uv run alembic upgrade head
uv run python -m scripts.seed_demo --password <password for the demo accounts>
```

The seed can also be run by hand in the container, e.g. to load the demo data
into a database that already has other vendors:
`docker compose exec app python -m scripts.seed_demo --password <password>`.

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
   location) and a **temporary** login (login ID and password), plus the
   vendor's own email and phone. The email is where "forgot password" links go.
2. Sign out, sign in with the temporary login. The vendor first picks its own
   login ID and password ("Set up your account"), then lands on its order
   board (with a short tutorial that uses practice orders). The temporary login
   ID stops working; the chosen one can never be changed.
3. 菜單管理 → 新增品項: names, category, price, prep time, description and
   photo, in Chinese and English. The item appears on the customer side right
   away; 店家設定 changes the store details and photos, and has a "Change
   password" button.

## Passwords

- **Change password** (signed in): customers on their profile page, vendors
  under 店家設定, admins at the top of the page. Every other device is signed
  out.
- **Forgot password** (on the sign-in page, for every account): enter the login
  ID or email, and a link is emailed to the account's email. It works once,
  for 30 minutes; using it signs the user in and out
  everywhere else. The page answers the same whether or not the account exists,
  and sends at most one email per account per minute.
- Sending email: set `MAIL_SMTP_HOST` etc. in `.env` (see `.env.example`; for
  Gmail, use an [app password](https://myaccount.google.com/apppasswords)).
  Without it, in development the email is printed in the server log instead:
  `docker compose logs app | grep -A 20 "Email not sent"`, then open the link.
- Links in the email point at `APP_URL` (default `http://localhost:8000`). For a
  demo over the local network, set it to the address the other computers open,
  e.g. `APP_URL=http://192.168.1.23:8000`.

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
