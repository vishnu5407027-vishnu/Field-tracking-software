from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, User
from core import live
from core.permissions import HasRole
from realtime.broadcast import broadcast_ingest_result
from fieldtasks.models import Task, TaskStatus

from . import services
from .models import Geofence, GeofenceEvent, Shift
from .serializers import (
    ClockSerializer,
    GeofenceEventSerializer,
    GeofenceSerializer,
    PingBatchSerializer,
    ShiftSerializer,
)


class StaffStatusView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.FIELD_STAFF,)
    serializer_class = ShiftSerializer  # OpenAPI hint

    def get(self, request):
        open_shift = (
            Shift.objects.filter(user=request.user, clock_out_at__isnull=True)
            .order_by("-clock_in_at")
            .first()
        )
        return Response(
            {
                "is_clocked_in": open_shift is not None,
                "shift": ShiftSerializer(open_shift).data if open_shift else None,
            }
        )


class StaffClockView(APIView):
    """Attendance control. Tracking only runs during an open shift: the
    mobile app starts location updates on clock-in and stops on clock-out,
    and the server clears the live marker so the dashboard map reflects
    off-duty status immediately."""

    permission_classes = [HasRole]
    allowed_roles = (Role.FIELD_STAFF,)
    serializer_class = ClockSerializer  # OpenAPI hint

    def patch(self, request):
        serializer = ClockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        open_shift = Shift.objects.filter(user=request.user, clock_out_at__isnull=True).first()

        if action == "in":
            if open_shift:
                raise ValidationError("Already clocked in")
            shift = Shift.objects.create(tenant_id=request.user.tenant_id, user=request.user)
            request.user.is_clocked_in = True
            request.user.save(update_fields=["is_clocked_in"])
            return Response({"is_clocked_in": True, "shift": ShiftSerializer(shift).data})

        if not open_shift:
            raise ValidationError("Not clocked in")
        open_shift.clock_out_at = timezone.now()
        open_shift.save(update_fields=["clock_out_at"])
        request.user.is_clocked_in = False
        request.user.save(update_fields=["is_clocked_in"])
        live.remove_live_location(str(request.user.tenant_id), str(request.user.id))
        return Response({"is_clocked_in": False, "shift": ShiftSerializer(open_shift).data})


class StaffLocationsView(APIView):
    """Offline-sync fallback for the mobile app: batched pings over REST."""

    permission_classes = [HasRole]
    allowed_roles = (Role.FIELD_STAFF,)
    serializer_class = PingBatchSerializer  # OpenAPI hint

    def post(self, request):
        serializer = PingBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pings = serializer.validated_data["pings"]

        result = services.ingest(request.user, pings)
        broadcast_ingest_result(str(request.user.tenant_id), result)
        return Response(
            {"accepted": len(pings), "transitions": result["transitions"]},
            status=status.HTTP_201_CREATED,
        )


class LiveLocationsView(APIView):
    """Current position of every clocked-in worker, served from Redis."""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)

    def get(self, request):
        return Response(live.get_live_locations(str(request.user.tenant_id)))


class LocationHistoryView(APIView):
    """Route playback: ?userId=...&date=YYYY-MM-DD"""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)

    def get(self, request):
        user_id = request.query_params.get("userId")
        date_str = request.query_params.get("date")
        if not user_id or not date_str:
            raise ValidationError("userId and date are required")
        try:
            return Response(services.history(request.user.tenant_id, user_id, date_str))
        except ValueError:
            raise ValidationError("date must be YYYY-MM-DD")


class GeofencesView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)
    serializer_class = GeofenceSerializer  # OpenAPI hint

    def get(self, request):
        fences = Geofence.objects.filter(tenant_id=request.user.tenant_id).order_by("-created_at")
        return Response(GeofenceSerializer(fences, many=True).data)

    def post(self, request):
        serializer = GeofenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fence = serializer.save(tenant_id=request.user.tenant_id)
        return Response(GeofenceSerializer(fence).data, status=status.HTTP_201_CREATED)


class GeofenceDetailView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)
    serializer_class = GeofenceSerializer  # OpenAPI hint

    def delete(self, request, pk):
        fence = Geofence.objects.filter(pk=pk, tenant_id=request.user.tenant_id).first()
        if fence is None:
            raise NotFound("Geofence not found")
        fence.delete()
        return Response({"deleted": True})


class GeofenceEventsView(APIView):
    """Check-in/check-out log, newest first. Optional ?userId= filter."""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)
    serializer_class = GeofenceEventSerializer  # OpenAPI hint

    def get(self, request):
        events = (
            GeofenceEvent.objects.filter(tenant_id=request.user.tenant_id)
            .select_related("geofence", "user")
            .order_by("-occurred_at")
        )
        if user_id := request.query_params.get("userId"):
            events = events.filter(user_id=user_id)
        return Response(GeofenceEventSerializer(events[:200], many=True).data)


class PerformanceReportView(APIView):
    """Per-staff productivity for one day: site visits, completed tasks,
    distance covered, active time, and hours on shift."""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)

    def get(self, request):
        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError("date is required (YYYY-MM-DD)")
        try:
            day_start, day_end = services.day_window_utc(date_str)
        except ValueError:
            raise ValidationError("date must be YYYY-MM-DD")

        tenant_id = request.user.tenant_id
        rows = []
        staff = User.objects.filter(tenant_id=tenant_id, role=Role.FIELD_STAFF).order_by(
            "first_name"
        )
        for member in staff:
            day = services.history(tenant_id, str(member.id), date_str)
            visits = GeofenceEvent.objects.filter(
                tenant_id=tenant_id,
                user=member,
                type="ENTER",
                occurred_at__gte=day_start,
                occurred_at__lt=day_end,
            ).count()
            tasks_completed = Task.objects.filter(
                tenant_id=tenant_id,
                field_staff=member,
                status=TaskStatus.COMPLETED,
                completed_at__gte=day_start,
                completed_at__lt=day_end,
            ).count()
            shift_seconds = sum(
                (
                    (min(s.clock_out_at or timezone.now(), day_end) - max(s.clock_in_at, day_start))
                    .total_seconds()
                )
                for s in Shift.objects.filter(
                    user=member, clock_in_at__lt=day_end
                ).exclude(clock_out_at__lt=day_start)
            )
            rows.append(
                {
                    "user_id": str(member.id),
                    "name": f"{member.first_name} {member.last_name}",
                    "visits": visits,
                    "tasks_completed": tasks_completed,
                    "distance_km": day["total_distance_km"],
                    "active_minutes": day["active_minutes"],
                    "hours_worked": round(max(shift_seconds, 0) / 3600, 1),
                }
            )
        return Response({"date": date_str, "staff": rows})
