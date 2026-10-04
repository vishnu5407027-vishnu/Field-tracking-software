import uuid

from django.conf import settings
from django.db import models

from accounts.models import Tenant


class TaskStatus(models.TextChoices):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE = "EN_ROUTE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProofType(models.TextChoices):
    PHOTO = "PHOTO"
    SIGNATURE = "SIGNATURE"
    NOTE = "NOTE"


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TaskStatus, default=TaskStatus.UNASSIGNED)
    lat = models.FloatField()
    lng = models.FloatField()
    address = models.CharField(max_length=300)

    dispatcher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tasks"
    )
    field_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )

    due_at = models.DateTimeField()
    # Set the first time the worker advances to EN_ROUTE — bounds the route
    # history shown for the task.
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["field_staff"]),
        ]

    def __str__(self) -> str:
        return self.title


class TaskProof(models.Model):
    """Proof-of-work attachment: a photo/signature URL or a free-text note."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="task_proofs")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="proofs")
    type = models.CharField(max_length=12, choices=ProofType)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["task"])]
