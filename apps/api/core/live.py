"""
Redis-backed live state: the latest position per on-duty worker (read by the
dashboard map in O(1)) and the set of geofences each worker is currently
inside (diffed on every ping to derive ENTER/EXIT events).

Key layout is per-tenant so cross-tenant reads are impossible by construction:
    tenant:{tenantId}:live              hash  userId -> JSON LiveLocation
    tenant:{tenantId}:inside:{userId}   set   geofence ids
"""

import json
from typing import Any

import redis
from django.conf import settings

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def set_live_location(tenant_id: str, location: dict[str, Any]) -> None:
    """`location` is a camelCase dict, stored verbatim — it is emitted as-is
    over both REST and WebSocket, so there is exactly one serialization."""
    get_client().hset(f"tenant:{tenant_id}:live", location["userId"], json.dumps(location))


def get_live_locations(tenant_id: str) -> list[dict[str, Any]]:
    raw = get_client().hgetall(f"tenant:{tenant_id}:live")
    return [json.loads(v) for v in raw.values()]


def remove_live_location(tenant_id: str, user_id: str) -> None:
    get_client().hdel(f"tenant:{tenant_id}:live", user_id)


def get_inside_geofences(tenant_id: str, user_id: str) -> set[str]:
    return set(get_client().smembers(f"tenant:{tenant_id}:inside:{user_id}"))


def set_inside_geofences(tenant_id: str, user_id: str, ids: list[str]) -> None:
    key = f"tenant:{tenant_id}:inside:{user_id}"
    pipe = get_client().pipeline()
    pipe.delete(key)
    if ids:
        pipe.sadd(key, *ids)
    pipe.execute()
