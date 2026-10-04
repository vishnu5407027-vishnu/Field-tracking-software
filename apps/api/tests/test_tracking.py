from datetime import datetime, timedelta, timezone

import pytest

from tracking.models import GeofenceEvent, LocationLog

pytestmark = pytest.mark.django_db


def ping(lat, lng, minutes_ago=0, **extra):
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {"lat": lat, "lng": lng, "recordedAt": at.isoformat(), **extra}


# ── Shifts ─────────────────────────────────────────────────────────────────


def test_clock_in_then_out(staff_client, staff):
    assert staff_client.get("/api/v1/staff/status").json()["isClockedIn"] is False

    response = staff_client.patch("/api/v1/staff/clock", {"action": "in"}, format="json")
    assert response.status_code == 200
    assert response.json()["isClockedIn"] is True
    assert response.json()["shift"]["clockOutAt"] is None

    # double clock-in rejected
    assert staff_client.patch(
        "/api/v1/staff/clock", {"action": "in"}, format="json"
    ).status_code == 400

    response = staff_client.patch("/api/v1/staff/clock", {"action": "out"}, format="json")
    assert response.json()["isClockedIn"] is False
    assert response.json()["shift"]["clockOutAt"] is not None


# ── Location ingestion + live map ──────────────────────────────────────────


def test_ping_batch_updates_live_cache(staff_client, admin_client, staff):
    response = staff_client.post(
        "/api/v1/staff/locations",
        {"pings": [ping(8.55, 76.88, minutes_ago=1, speed=4.2, batteryLevel=80.0)]},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["accepted"] == 1
    assert LocationLog.objects.count() == 1

    live = admin_client.get("/api/v1/locations/live").json()
    assert len(live) == 1
    assert live[0]["userId"] == str(staff.id)
    assert live[0]["batteryLevel"] == 80.0


def test_clock_out_clears_live_marker(staff_client, admin_client):
    staff_client.patch("/api/v1/staff/clock", {"action": "in"}, format="json")
    staff_client.post(
        "/api/v1/staff/locations", {"pings": [ping(8.55, 76.88)]}, format="json"
    )
    assert len(admin_client.get("/api/v1/locations/live").json()) == 1

    staff_client.patch("/api/v1/staff/clock", {"action": "out"}, format="json")
    assert admin_client.get("/api/v1/locations/live").json() == []


def test_staff_cannot_read_live_locations(staff_client):
    assert staff_client.get("/api/v1/locations/live").status_code == 403


# ── Geofence transitions ───────────────────────────────────────────────────


def test_geofence_enter_then_exit(staff_client, admin_client, staff, tenant):
    admin_client.post(
        "/api/v1/geofences",
        {"name": "Client HQ", "lat": 8.5566, "lng": 76.8810, "radiusM": 250},
        format="json",
    )

    # First ping inside the fence -> ENTER
    response = staff_client.post(
        "/api/v1/staff/locations",
        {"pings": [ping(8.5566, 76.8810, minutes_ago=2)]},
        format="json",
    )
    transitions = response.json()["transitions"]
    assert [t["type"] for t in transitions] == ["ENTER"]
    assert transitions[0]["geofenceName"] == "Client HQ"

    # Second ping inside -> no new transition
    response = staff_client.post(
        "/api/v1/staff/locations",
        {"pings": [ping(8.5567, 76.8811, minutes_ago=1)]},
        format="json",
    )
    assert response.json()["transitions"] == []

    # Ping far away -> EXIT
    response = staff_client.post(
        "/api/v1/staff/locations", {"pings": [ping(8.60, 76.95)]}, format="json"
    )
    assert [t["type"] for t in response.json()["transitions"]] == ["EXIT"]

    events = admin_client.get("/api/v1/geofences/events").json()
    assert [e["type"] for e in events] == ["EXIT", "ENTER"]  # newest first
    assert events[0]["user"]["firstName"] == "Ravi"
    assert events[0]["geofence"]["name"] == "Client HQ"


# ── History / playback analytics ───────────────────────────────────────────


def test_history_distance_and_idle_split(admin_client, staff, tenant):
    base = datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc)
    # Three points one minute apart, ~111m each step (0.001 deg lat).
    # First leg: prev speed 0 (idle), second leg: prev speed 2 m/s (active).
    for i, speed in enumerate([0.0, 2.0, 2.0]):
        LocationLog.objects.create(
            tenant=tenant, user=staff,
            lat=8.5 + i * 0.001, lng=76.9, speed=speed,
            recorded_at=base + timedelta(minutes=i),
        )

    response = admin_client.get(
        f"/api/v1/locations/history?userId={staff.id}&date=2026-06-10"
    )
    body = response.json()
    assert len(body["points"]) == 3
    assert body["totalDistanceKm"] == pytest.approx(0.22, abs=0.01)
    assert body["idleMinutes"] == 1
    assert body["activeMinutes"] == 1

    # Other days are empty
    empty = admin_client.get(
        f"/api/v1/locations/history?userId={staff.id}&date=2026-06-11"
    ).json()
    assert empty["points"] == []


def test_performance_report(admin_client, staff, tenant):
    response = admin_client.get("/api/v1/reports/performance?date=2026-06-10")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-06-10"
    assert body["staff"][0]["name"] == "Ravi Kumar"
    assert {"visits", "tasksCompleted", "distanceKm", "hoursWorked"} <= set(body["staff"][0])
