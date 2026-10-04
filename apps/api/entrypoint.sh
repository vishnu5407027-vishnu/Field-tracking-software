#!/bin/sh
set -e

echo "Waiting for the database..."
python - <<'PY'
import os, time, sys
import psycopg

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        psycopg.connect(url, connect_timeout=3).close()
        sys.exit(0)
    except Exception:
        time.sleep(2)
print("Database never became ready", file=sys.stderr)
sys.exit(1)
PY

python manage.py migrate --noinput
if [ "${SEED_DEMO:-1}" = "1" ]; then
  python manage.py seed_demo
fi
python manage.py collectstatic --noinput

# Daphne serves both HTTP (DRF) and WebSockets (Channels) on one port.
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
