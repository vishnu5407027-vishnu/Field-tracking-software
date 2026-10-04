# FieldTracking — Field Sales/Staff Tracking Platform

Multi-tenant SaaS for tracking and managing field teams: real-time location,
attendance, route playback, geofenced site visits, task dispatch with proof
of work, and per-staff performance analytics.

| App | Path | Stack | Purpose |
|---|---|---|---|
| API | `apps/api` | Python, Django 5, DRF, Channels, PostgreSQL + TimescaleDB, Redis | Multi-tenant backend, location ingestion, realtime broadcast |
| Web | `apps/web` | Next.js 14, TailwindCSS, react-leaflet | Owner portal (`/owner`) + tenant dashboard (`/dashboard`) |
| Mobile | `apps/mobile` | Flutter, geolocator, sqflite | Field staff app: shift control, background tracking, offline sync, tasks |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Quick start (Docker)

Prerequisite: Docker Desktop.

```bash
docker compose up -d --build
```

That brings up everything: TimescaleDB (host port **5433**), Redis (6379),
the Django API (8000), and the web app (3000). On startup the API container
runs migrations (converting `LocationLog` into a Timescale hypertable) and
seeds demo data — then open http://localhost:3000.

Interactive API docs: http://localhost:8000/api/docs/

## Local development (without Docker for the apps)

```bash
docker compose up -d db redis        # infrastructure only

# API
cd apps/api
python -m venv .venv
.venv/Scripts/activate               # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8000      # serves REST + WebSockets (Daphne)

# Web (second terminal)
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev                          # http://localhost:3000
```

Run the backend tests with `python -m pytest` inside `apps/api`.

### Demo logins (password: `Password123!`)

| Email | Role | Lands on |
|---|---|---|
| `owner@fieldtracking.dev` | SUPER_ADMIN | Owner portal |
| `admin@acme.test` | TENANT_ADMIN | Tenant dashboard |
| `dispatch@acme.test` | DISPATCHER | Tenant dashboard |
| `ravi@acme.test` / `priya@acme.test` | FIELD_STAFF | Mobile app |

### Mobile app (Flutter)

```bash
cd apps/mobile
flutter create . --org dev.fieldtracking --project-name fieldtracking
flutter pub get
flutter run        # emulator; see apps/mobile/README.md for devices & permissions
```

### Simulating a field worker without a phone

Log in as a field worker via REST, clock in, and post pings:

```bash
TOKEN=$(curl -s localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"ravi@acme.test","password":"Password123!"}' | jq -r .accessToken)
curl -X PATCH localhost:8000/api/v1/staff/clock -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"action":"in"}'
curl -X POST localhost:8000/api/v1/staff/locations -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"pings\":[{\"lat\":8.5566,\"lng\":76.8810,\"speed\":4.2,\"recordedAt\":\"$(date -u +%FT%TZ)\"}]}"
```

The marker appears on the dashboard live map in real time, and entering the
seeded "Client HQ — Technopark" geofence logs a check-in event.
