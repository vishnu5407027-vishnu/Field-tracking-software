# Architecture

## System overview

```
[Field Staff Mobile App — Flutter]
      │  HTTPS REST (auth, tasks, clock in/out, offline batch sync)
      │  WebSocket  (optional live location_ping while online)
      ▼
[Django API — DRF + Channels (Daphne, ASGI)]
      ├─► Redis        — latest location per user (live map), geofence inside-state,
      │                  Channels group fan-out
      ├─► PostgreSQL   — relational data + LocationLog hypertable (TimescaleDB)
      └─► WebSocket    — broadcast to group `tenant.{id}`:
                          location_sync · geofence_event · task_updated
                              ▼
                  [Tenant Web Dashboard — Next.js]
```

**Ping lifecycle:** mobile buffers pings in SQLite → flushes batches to
`POST /staff/locations` → the API persists the batch to the `LocationLog`
hypertable, overwrites the user's entry in the per-tenant Redis live hash,
diffs geofence containment against the previous state to emit ENTER/EXIT
events → broadcasts to the tenant's Channels group only
([tracking/services.py](../apps/api/tracking/services.py)).

**Wire format:** camelCase JSON on the wire, snake_case in Python — the
`djangorestframework-camel-case` renderer/parser pair translates at the API
boundary, and WebSocket payloads are camelized in
[realtime/broadcast.py](../apps/api/realtime/broadcast.py).

## Multi-tenancy (logical isolation)

Single database; every tenant-owned table carries `tenant_id`. Defense in
depth, all keyed off the JWT — the tenant is **never** read from a request
body or URL:

1. **JWT claims** ([core/jwt.py](../apps/api/core/jwt.py)): tokens carry
   `{sub, tenantId, role}`; DRF's `JWTAuthentication` resolves the user, and
   the WebSocket consumer reads the same verified claims on connect.
2. **Queryset scoping**: every view filters on
   `request.user.tenant_id`, and mutations re-verify ownership with a scoped
   lookup before touching a row (e.g. staff can only PATCH their own tasks).
3. **Role permissions** ([core/permissions.py](../apps/api/core/permissions.py)):
   `HasRole` checks `allowed_roles` per view/method.
4. **Group-scoped realtime**: each socket joins only `tenant.{id}`;
   broadcasts never target anything wider.

The owner portal endpoints operate across tenants deliberately —
`SUPER_ADMIN` has no tenant. For stricter guarantees, add native Postgres
RLS (`SET LOCAL app.current_tenant_id`) as a further layer.

## High-volume location data

- **Hot path (live map):** Redis hash `tenant:{id}:live` keyed by userId —
  one O(1) read for the whole map, overwritten on every ping, cleared on
  clock-out ([core/live.py](../apps/api/core/live.py)).
- **Cold path (history):** `LocationLog` becomes a TimescaleDB hypertable
  partitioned on `recorded_at`
  ([migration 0002](../apps/api/tracking/migrations/0002_locationlog_hypertable.py));
  the migration is a safe no-op without the extension. Playback queries hit
  the `(tenant, user, recorded_at DESC)` index within a day's chunk.
- Mobile batches pings (~20 per upload), so write amplification stays low.
  At larger scale, put a queue (Celery/Kafka) between ingestion and the DB
  writer and use `COPY`-style batch inserts.

## Realtime

Django Channels with the Redis channel layer. One consumer
([realtime/consumers.py](../apps/api/realtime/consumers.py)) serves both
directions: dashboards subscribe to their tenant group; field apps may push
`location_ping` frames over the same socket. REST views fan out through
`group_send`, so events reach every dashboard replica regardless of which
process handled the HTTP request — multi-instance fan-out works out of the
box because the group membership lives in Redis.

## Battery & privacy on mobile

- Tracking starts **only on clock-in** and stops on clock-out (also clears
  the live marker server-side). Off-shift, no location code runs.
- Pulsing: 50 m distance filter / 60 s interval; the OS suspends GPS when
  stationary. Android runs a foreground service with a persistent
  notification; iOS uses `UIBackgroundModes: location`.
- Offline-first: every ping lands in SQLite before any network attempt;
  a 30-second flusher drains the queue whenever connectivity returns
  ([ping_queue.dart](../apps/mobile/lib/src/services/ping_queue.dart)).

## RBAC

| Role | Scope |
|---|---|
| SUPER_ADMIN | Owner portal: tenant CRUD, suspend, platform analytics, MRR |
| TENANT_ADMIN | Team management, plus everything DISPATCHER can do |
| DISPATCHER | Live map, playback, tasks, geofences, performance reports |
| FIELD_STAFF | Mobile only: own tasks, clock in/out, location upload |

Seat limits are enforced at field-staff invite time against
`Tenant.seat_limit`.

## Performance analytics

`GET /reports/performance?date=` aggregates per staff member: geofence
check-ins (site visits), completed tasks, distance covered, active minutes
(speed-based idle split), and hours on shift — surfaced on the dashboard's
Performance page.

## Deliberate scaffold simplifications

- Billing: plan tiers + seat limits are modeled and MRR is computed, but the
  Razorpay webhook/subscription flow is stubbed (`razorpay_customer_id`).
- Proof-of-work uploads store URLs/text; wire S3/GCS presigned uploads.
- Geofence checks load fences per ping — cache per tenant in Redis at scale.
- Access tokens live 12 h; the login response includes a refresh token but
  clients don't rotate yet.
