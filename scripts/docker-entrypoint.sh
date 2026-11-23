#!/bin/sh
# Runs every time the app container starts (the Dockerfile's ENTRYPOINT), before the app:
# 1. Brings the database up to date with the migrations (does nothing when it already is).
# 2. If DEMO_PASSWORD is set: on the first start only, loads the NTHU stalls, menus and
#    the demo accounts. Later starts leave the data alone, so whatever was changed in the
#    app (prices, sold-out items, new stalls) survives a restart.
# 3. Starts the Dockerfile's CMD (uvicorn).
# If a step fails the container stops; `docker compose logs app` shows why.
set -eu

echo "Applying database migrations..."
alembic upgrade head

if [ -n "${DEMO_PASSWORD:-}" ]; then
    python -m scripts.seed_demo --if-empty
else
    echo "DEMO_PASSWORD is not set: not loading the demo stalls and accounts."
fi

exec "$@"
