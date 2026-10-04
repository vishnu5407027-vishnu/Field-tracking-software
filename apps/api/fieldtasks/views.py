import os
import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, User
from core import live
from core.permissions import HasRole
from realtime.broadcast import broadcast_task_update
from tracking import services

from .models import Task, TaskProof, TaskStatus
from .serializers import (
    AddProofSerializer,
    CreateTaskSerializer,
    TaskProofSerializer,
    TaskSerializer,
    UpdateTaskStatusSerializer,
)

# Statuses where the assignee is still working the task (live trail relevant).
ACTIVE_STATUSES = (TaskStatus.ASSIGNED, TaskStatus.EN_ROUTE, TaskStatus.IN_PROGRESS)


def _task_queryset(tenant_id):
    return (
        Task.objects.filter(tenant_id=tenant_id)
        .select_related("field_staff")
        .prefetch_related("proofs")
    )


class TasksView(APIView):
    """Dashboard dispatch: list with optional ?status= / ?fieldStaffId= filters."""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)
    serializer_class = TaskSerializer  # OpenAPI hint

    def get(self, request):
        tasks = _task_queryset(request.user.tenant_id).order_by("due_at")
        if status_filter := request.query_params.get("status"):
            tasks = tasks.filter(status=status_filter)
        if staff_filter := request.query_params.get("fieldStaffId"):
            tasks = tasks.filter(field_staff_id=staff_filter)
        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request):
        serializer = CreateTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        field_staff = None
        if data.get("field_staff_id"):
            field_staff = User.objects.filter(
                pk=data["field_staff_id"],
                tenant_id=request.user.tenant_id,
                role=Role.FIELD_STAFF,
            ).first()
            if field_staff is None:
                raise ValidationError("Unknown field staff")

        task = Task.objects.create(
            tenant_id=request.user.tenant_id,
            title=data["title"],
            description=data.get("description"),
            lat=data["lat"],
            lng=data["lng"],
            address=data["address"],
            due_at=data["due_at"],
            dispatcher=request.user,
            field_staff=field_staff,
            status=TaskStatus.ASSIGNED if field_staff else TaskStatus.UNASSIGNED,
        )
        payload = TaskSerializer(task).data
        broadcast_task_update(str(request.user.tenant_id), payload)
        return Response(payload, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    """Single task with proofs, for the dashboard detail page."""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)
    serializer_class = TaskSerializer  # OpenAPI hint

    def get(self, request, pk):
        task = _task_queryset(request.user.tenant_id).filter(pk=pk).first()
        if task is None:
            raise NotFound("Task not found")
        return Response(TaskSerializer(task).data)


class TaskRouteView(APIView):
    """The assignee's travelled route for a task, plus their live position
    while the task is still active. Drives the detail-page map."""

    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN, Role.DISPATCHER)

    def get(self, request, pk):
        task = _task_queryset(request.user.tenant_id).filter(pk=pk).first()
        if task is None:
            raise NotFound("Task not found")

        result = {
            "status": task.status,
            "destination": {"lat": task.lat, "lng": task.lng},
            "points": [],
            "total_distance_km": 0,
            "duration_minutes": 0,
            "live": None,
        }

        if task.field_staff_id:
            start = task.started_at or task.created_at
            end = task.completed_at or timezone.now()
            route = services.route_between(
                request.user.tenant_id, str(task.field_staff_id), start, end
            )
            result.update(route)

            if task.status in ACTIVE_STATUSES:
                live_all = live.get_live_locations(str(request.user.tenant_id))
                result["live"] = next(
                    (l for l in live_all if l["userId"] == str(task.field_staff_id)), None
                )

        return Response(result)


class StaffTasksView(APIView):
    """Mobile: the worker's open tasks (default) or completed/cancelled
    history with ?completed=1, most recent first."""

    permission_classes = [HasRole]
    allowed_roles = (Role.FIELD_STAFF,)
    serializer_class = TaskSerializer  # OpenAPI hint

    def get(self, request):
        tasks = _task_queryset(request.user.tenant_id).filter(field_staff=request.user)
        completed = request.query_params.get("completed") in ("1", "true", "True")
        if completed:
            tasks = tasks.filter(
                status__in=[TaskStatus.COMPLETED, TaskStatus.CANCELLED]
            ).order_by("-completed_at")
        else:
            tasks = tasks.exclude(
                status__in=[TaskStatus.COMPLETED, TaskStatus.CANCELLED]
            ).order_by("due_at")
        return Response(TaskSerializer(tasks, many=True).data)


class StaffTaskDetailView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.FIELD_STAFF,)
    serializer_class = TaskSerializer  # OpenAPI hint

    def get_task(self, request, pk) -> Task:
        task = (
            _task_queryset(request.user.tenant_id)
            .filter(pk=pk, field_staff=request.user)
            .first()
        )
        if task is None:
            raise NotFound("Task not found")
        return task

    def get(self, request, pk):
        return Response(TaskSerializer(self.get_task(request, pk)).data)

    def patch(self, request, pk):
        task = self.get_task(request, pk)
        serializer = UpdateTaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task.status = serializer.validated_data["status"]
        fields = ["status"]
        # Stamp the first EN_ROUTE so the travelled-route window has a start.
        if task.status == TaskStatus.EN_ROUTE and task.started_at is None:
            task.started_at = timezone.now()
            fields.append("started_at")
        if task.status == TaskStatus.COMPLETED:
            task.completed_at = timezone.now()
            fields.append("completed_at")
        task.save(update_fields=fields)
        payload = TaskSerializer(task).data
        broadcast_task_update(str(request.user.tenant_id), payload)
        return Response(payload)


class StaffTaskProofsView(StaffTaskDetailView):
    serializer_class = TaskProofSerializer  # OpenAPI hint

    def post(self, request, pk):
        task = self.get_task(request, pk)
        serializer = AddProofSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proof = TaskProof.objects.create(
            tenant_id=request.user.tenant_id,
            task=task,
            type=serializer.validated_data["type"],
            content=serializer.validated_data["content"],
        )
        return Response(TaskProofSerializer(proof).data, status=status.HTTP_201_CREATED)


class StaffTaskPhotoView(StaffTaskDetailView):
    """Multipart photo upload from the mobile camera. Stores the file and
    records a PHOTO proof whose content is the relative media URL."""

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = TaskProofSerializer  # OpenAPI hint

    def post(self, request, pk):
        task = self.get_task(request, pk)
        upload = request.FILES.get("photo")
        if upload is None:
            raise ValidationError("No photo provided")
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError("Photo too large (max 10 MB)")

        ext = os.path.splitext(upload.name)[1].lower() or ".jpg"
        saved_path = default_storage.save(f"proofs/{uuid.uuid4().hex}{ext}", upload)
        proof = TaskProof.objects.create(
            tenant_id=request.user.tenant_id,
            task=task,
            type="PHOTO",
            content=f"/media/{saved_path}",
        )
        return Response(TaskProofSerializer(proof).data, status=status.HTTP_201_CREATED)
