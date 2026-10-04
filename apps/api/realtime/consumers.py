"""
Single WebSocket endpoint for both producers (mobile apps sending
location_ping) and consumers (dashboards receiving location_sync /
geofence_event / task_updated).

Auth: `?token=<JWT>` on the connection URL. The tenant and role are read
from verified token claims, and the socket is locked into its tenant group.
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from djangorestframework_camel_case.util import underscoreize
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .broadcast import group_for

logger = logging.getLogger(__name__)


class LiveConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            query = parse_qs(self.scope.get("query_string", b"").decode())
            token = AccessToken(query.get("token", [""])[0])
        except TokenError as err:
            logger.warning("Rejected socket connection: %s", err)
            await self.close(code=4401)
            return

        self.user_id = str(token["sub"])
        self.tenant_id = token.get("tenantId")
        self.role = token.get("role")

        if self.tenant_id:
            await self.channel_layer.group_add(group_for(self.tenant_id), self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        # Live markers are cleared on clock-out, not on transient disconnects.
        if getattr(self, "tenant_id", None):
            await self.channel_layer.group_discard(group_for(self.tenant_id), self.channel_name)

    async def receive_json(self, content):
        if content.get("event") != "location_ping":
            return
        if self.role != "FIELD_STAFF" or not self.tenant_id:
            return

        body = content.get("data") or []
        raw_pings = body if isinstance(body, list) else [body]
        accepted = await self._ingest(raw_pings)
        await self.send_json({"event": "ack", "data": {"accepted": accepted}})

    @database_sync_to_async
    def _ingest(self, raw_pings: list[dict]) -> int:
        # Imported lazily: consumers load before Django apps during ASGI boot.
        from accounts.models import User
        from realtime.broadcast import broadcast_ingest_result
        from tracking import services
        from tracking.serializers import PingSerializer

        serializer = PingSerializer(data=underscoreize(raw_pings), many=True)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(pk=self.user_id)
        result = services.ingest(user, serializer.validated_data)
        broadcast_ingest_result(self.tenant_id, result)
        return len(serializer.validated_data)

    async def broadcast_message(self, event):
        await self.send_json({"event": event["event"], "data": event["data"]})
