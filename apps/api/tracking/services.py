"""
Location pipeline: persist pings, refresh the Redis live cache, and diff the
latest point against tenant geofences to emit ENTER/EXIT transitions.
Pure functions over the ORM + live store so both the REST endpoint and the
WebSocket consumer share one implementation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from core import live
from core.geo import haversine_meters

from .models import Geofence, GeofenceEvent, LocationLog

# Below this speed (m/s) a point counts as idle for playback analytics.
IDLE_SPEED_MS = 0.5
# Gaps longer than this between pings are not attributed to either bucket.
MAX_GAP_SECONDS = 300


def ingest(user, pings: list[dict[str, Any]]) -> dict[str, Any]:
    """`pings` are validated dicts with snake_case keys (lat, lng, speed,
    heading, accuracy, battery_level, recorded_at: datetime). Returns the
    camelCase live location + transitions, ready to broadcast."""
    if not pings:
        return {"latest": None, "transitions": []}

    tenant_id = str(user.tenant_id)
    ordered = sorted(pings, key=lambda p: p["recorded_at"])

    LocationLog.objects.bulk_create(
        LocationLog(
            tenant_id=user.tenant_id,
            user_id=user.id,
            lat=p["lat"],
            lng=p["lng"],
            speed=p.get("speed"),
            heading=p.get("heading"),
            accuracy=p.get("accuracy"),
            battery_level=p.get("battery_level"),
            recorded_at=p["recorded_at"],
        )
        for p in ordered
    )

    last = ordered[-1]
    latest = {
        "userId": str(user.id),
        "lat": last["lat"],
        "lng": last["lng"],
        "speed": last.get("speed"),
        "heading": last.get("heading"),
        "batteryLevel": last.get("battery_level"),
        "recordedAt": last["recorded_at"].isoformat().replace("+00:00", "Z"),
    }
    live.set_live_location(tenant_id, latest)

    transitions = _detect_geofence_transitions(user, last)
    return {"latest": latest, "transitions": transitions}


def _detect_geofence_transitions(user, point: dict[str, Any]) -> list[dict[str, Any]]:
    fences = list(Geofence.objects.filter(tenant_id=user.tenant_id))
    if not fences:
        return []

    tenant_id, user_id = str(user.tenant_id), str(user.id)
    inside_now = {
        str(f.id): f
        for f in fences
        if haversine_meters(point["lat"], point["lng"], f.lat, f.lng) <= f.radius_m
    }
    inside_before = live.get_inside_geofences(tenant_id, user_id)
    occurred_at = point["recorded_at"]

    transitions = [
        {"geofence": f, "type": "ENTER"}
        for fid, f in inside_now.items()
        if fid not in inside_before
    ] + [
        {"geofence": f, "type": "EXIT"}
        for f in fences
        if str(f.id) in inside_before and str(f.id) not in inside_now
    ]

    if transitions:
        GeofenceEvent.objects.bulk_create(
            GeofenceEvent(
                tenant_id=user.tenant_id,
                geofence=t["geofence"],
                user_id=user.id,
                type=t["type"],
                occurred_at=occurred_at,
            )
            for t in transitions
        )

    live.set_inside_geofences(tenant_id, user_id, list(inside_now.keys()))

    occurred_iso = occurred_at.isoformat().replace("+00:00", "Z")
    return [
        {
            "geofenceId": str(t["geofence"].id),
            "geofenceName": t["geofence"].name,
            "userId": user_id,
            "type": t["type"],
            "occurredAt": occurred_iso,
        }
        for t in transitions
    ]


def day_window_utc(date_str: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def history(tenant_id, user_id: str, date_str: str) -> dict[str, Any]:
    """Route playback for one user on one UTC calendar day, with distance
    and an idle/active time split."""
    day_start, day_end = day_window_utc(date_str)
    points = list(
        LocationLog.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            recorded_at__gte=day_start,
            recorded_at__lt=day_end,
        )
        .order_by("recorded_at")
        .values("lat", "lng", "speed", "heading", "recorded_at")
    )

    distance_m, idle_seconds, active_seconds = _route_stats(points)
    return {
        "points": [
            {
                "lat": p["lat"],
                "lng": p["lng"],
                "speed": p["speed"],
                "heading": p["heading"],
                "recorded_at": p["recorded_at"],
            }
            for p in points
        ],
        "total_distance_km": round(distance_m / 1000, 2),
        "idle_minutes": round(idle_seconds / 60),
        "active_minutes": round(active_seconds / 60),
    }


def route_between(tenant_id, user_id: str, start, end) -> dict[str, Any]:
    """Ordered location points for a user within [start, end], with total
    distance and elapsed minutes — used to draw a task's travelled route."""
    points = list(
        LocationLog.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            recorded_at__gte=start,
            recorded_at__lt=end,
        )
        .order_by("recorded_at")
        .values("lat", "lng", "recorded_at")
    )
    distance_m = 0.0
    for prev, cur in zip(points, points[1:]):
        distance_m += haversine_meters(prev["lat"], prev["lng"], cur["lat"], cur["lng"])
    duration_min = 0
    if len(points) >= 2:
        duration_min = round(
            (points[-1]["recorded_at"] - points[0]["recorded_at"]).total_seconds() / 60
        )
    return {
        "points": [
            {"lat": p["lat"], "lng": p["lng"], "recorded_at": p["recorded_at"]}
            for p in points
        ],
        "total_distance_km": round(distance_m / 1000, 2),
        "duration_minutes": duration_min,
    }


def _route_stats(points: list[dict[str, Any]]) -> tuple[float, float, float]:
    distance_m = idle_seconds = active_seconds = 0.0
    for prev, cur in zip(points, points[1:]):
        distance_m += haversine_meters(prev["lat"], prev["lng"], cur["lat"], cur["lng"])
        gap = (cur["recorded_at"] - prev["recorded_at"]).total_seconds()
        if gap > MAX_GAP_SECONDS:
            continue
        if (prev["speed"] or 0) < IDLE_SPEED_MS:
            idle_seconds += gap
        else:
            active_seconds += gap
    return distance_m, idle_seconds, active_seconds
