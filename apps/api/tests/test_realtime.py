import json
import uuid
from datetime import datetime, timezone

import pytest

from djangorestframework_camel_case.util import camelize

from fieldtasks.models import Task, TaskStatus
from fieldtasks.serializers import TaskSerializer
from realtime.broadcast import _json_safe

pytestmark = pytest.mark.django_db


def test_json_safe_normalizes_uuid_and_datetime():
    raw = {"id": uuid.uuid4(), "when": datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc)}
    safe = _json_safe(raw)
    assert isinstance(safe["id"], str)
    json.dumps(safe)  # must not raise


def test_task_broadcast_payload_is_json_serializable(admin, staff):
    """Regression: a serialized task carries raw UUIDs (dispatcher_id,
    field_staff_id) that crash the msgpack channel layer unless normalized."""
    task = Task.objects.create(
        tenant=staff.tenant,
        title="AC inspection",
        lat=8.55,
        lng=76.88,
        address="Site",
        dispatcher=admin,
        field_staff=staff,
        due_at=datetime(2026, 6, 13, 9, 0, tzinfo=timezone.utc),
        status=TaskStatus.ASSIGNED,
    )

    raw = camelize(TaskSerializer(task).data)
    # The raw payload still holds a UUID object — proves the hazard is real.
    assert isinstance(raw["fieldStaffId"], uuid.UUID)

    payload = _json_safe(raw)
    json.dumps(payload)  # must not raise
    assert isinstance(payload["fieldStaffId"], str)
    assert payload["fieldStaff"]["firstName"] == "Ravi"
