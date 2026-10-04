from rest_framework import serializers

from .models import Geofence, GeofenceEvent, Shift


class PingSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    speed = serializers.FloatField(required=False, allow_null=True)
    heading = serializers.FloatField(required=False, allow_null=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    battery_level = serializers.FloatField(required=False, allow_null=True)
    recorded_at = serializers.DateTimeField()


class PingBatchSerializer(serializers.Serializer):
    pings = PingSerializer(many=True)


class ClockSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["in", "out"])


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["id", "user_id", "clock_in_at", "clock_out_at"]


class GeofenceSerializer(serializers.ModelSerializer):
    radius_m = serializers.FloatField(min_value=10)

    class Meta:
        model = Geofence
        fields = ["id", "name", "lat", "lng", "radius_m", "created_at"]


class GeofenceEventSerializer(serializers.ModelSerializer):
    geofence = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = GeofenceEvent
        fields = ["id", "type", "occurred_at", "geofence", "user"]

    def get_geofence(self, event) -> dict:
        return {"name": event.geofence.name}

    def get_user(self, event) -> dict:
        return {"first_name": event.user.first_name, "last_name": event.user.last_name}
