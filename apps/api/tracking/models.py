import uuid

from django.conf import settings
from django.db import models

from accounts.models import Tenant


class Shift(models.Model):
    """One attendance interval: clock-in to clock-out."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="shifts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shifts"
    )
    clock_in_at = models.DateTimeField(auto_now_add=True)
    clock_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "user", "clock_in_at"])]


class Geofence(models.Model):
    """Circular site boundary; crossing it produces check-in/out events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="geofences")
    name = models.CharField(max_length=120)
    lat = models.FloatField()
    lng = models.FloatField()
    radius_m = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["tenant"])]

    def __str__(self) -> str:
        return self.name


class GeofenceEventType(models.TextChoices):
    ENTER = "ENTER"
    EXIT = "EXIT"


class GeofenceEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="geofence_events")
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, related_name="events")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="geofence_events"
    )
    type = models.CharField(max_length=10, choices=GeofenceEventType)
    occurred_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "geofence", "occurred_at"]),
            models.Index(fields=["tenant", "user", "occurred_at"]),
        ]


class LocationLog(models.Model):
    """High-volume GPS ping history. On PostgreSQL+TimescaleDB this table is
    converted to a hypertable partitioned on recorded_at (see migration
    0002); rows are insert-only."""

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="location_logs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="location_logs"
    )
    lat = models.FloatField()
    lng = models.FloatField()
    speed = models.FloatField(null=True, blank=True)  # m/s
    heading = models.FloatField(null=True, blank=True)  # degrees
    accuracy = models.FloatField(null=True, blank=True)  # meters
    battery_level = models.FloatField(null=True, blank=True)  # 0-100
    recorded_at = models.DateTimeField()  # device timestamp
    created_at = models.DateTimeField(auto_now_add=True)  # server arrival

    class Meta:
        indexes = [models.Index(fields=["tenant", "user", "-recorded_at"])]
