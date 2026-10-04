"""
Fan-out to dashboard WebSocket clients. Every event targets one tenant group,
so cross-tenant traffic is impossible by construction.

Wire format (matches the web client): {"event": <name>, "data": <payload>}
Events: location_sync, geofence_event, task_updated.
"""

import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder
from djangorestframework_camel_case.util import camelize


def group_for(tenant_id: str) -> str:
    return f"tenant.{tenant_id}"


def _json_safe(data):
    """Reduce a payload to plain JSON types.

    The Redis channel layer (msgpack) and the consumer's `send_json` cannot
    encode UUID / datetime / Decimal — DRF only applies its own encoder on the
    HTTP response path. Normalise here so fan-out never crashes on, e.g., a
    raw `field_staff_id` UUID in a serialized task.
    """
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def broadcast_to_tenant(tenant_id: str, event: str, data) -> None:
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        group_for(tenant_id),
        {"type": "broadcast.message", "event": event, "data": _json_safe(data)},
    )


def broadcast_ingest_result(tenant_id: str, result: dict) -> None:
    """`result` comes from tracking.services.ingest — already camelCase."""
    if result["latest"]:
        broadcast_to_tenant(tenant_id, "location_sync", result["latest"])
    for transition in result["transitions"]:
        broadcast_to_tenant(tenant_id, "geofence_event", transition)


def broadcast_task_update(tenant_id: str, task_payload: dict) -> None:
    """`task_payload` is snake_case serializer output; the HTTP renderer
    camelizes responses but WS messages must be camelized here."""
    broadcast_to_tenant(tenant_id, "task_updated", camelize(task_payload))
