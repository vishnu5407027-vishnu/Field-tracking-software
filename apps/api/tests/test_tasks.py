from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.django_db

TASKS = "/api/v1/tasks"


def task_payload(**overrides):
    payload = {
        "title": "AC unit inspection",
        "address": "Technopark Campus",
        "lat": 8.5566,
        "lng": 76.8810,
        "dueAt": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_dispatch_and_complete_flow(admin_client, staff_client, staff):
    response = admin_client.post(
        TASKS, task_payload(fieldStaffId=str(staff.id)), format="json"
    )
    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "ASSIGNED"
    assert task["fieldStaff"]["firstName"] == "Ravi"

    # Staff sees it in their open list
    my_tasks = staff_client.get("/api/v1/staff/tasks").json()
    assert [t["id"] for t in my_tasks] == [task["id"]]

    # Advance through the lifecycle
    for status in ("EN_ROUTE", "IN_PROGRESS", "COMPLETED"):
        response = staff_client.patch(
            f"/api/v1/staff/tasks/{task['id']}", {"status": status}, format="json"
        )
        assert response.status_code == 200, response.content
    assert response.json()["completedAt"] is not None

    # Completed tasks drop out of the staff list
    assert staff_client.get("/api/v1/staff/tasks").json() == []


def test_unassigned_task_status(admin_client):
    response = admin_client.post(TASKS, task_payload(), format="json")
    assert response.json()["status"] == "UNASSIGNED"
    assert response.json()["fieldStaff"] is None


def test_staff_cannot_touch_others_tasks(admin_client, staff_client, tenant, staff):
    from accounts.models import Role, User

    other = User.objects.create_user(
        email="other@test.dev", password="Password123!",
        first_name="Priya", last_name="Sharma", role=Role.FIELD_STAFF, tenant=tenant,
    )
    task = admin_client.post(
        TASKS, task_payload(fieldStaffId=str(other.id)), format="json"
    ).json()
    response = staff_client.patch(
        f"/api/v1/staff/tasks/{task['id']}", {"status": "EN_ROUTE"}, format="json"
    )
    assert response.status_code == 404


def test_proof_attachment(admin_client, staff_client, staff):
    task = admin_client.post(
        TASKS, task_payload(fieldStaffId=str(staff.id)), format="json"
    ).json()
    response = staff_client.post(
        f"/api/v1/staff/tasks/{task['id']}/proofs",
        {"type": "NOTE", "content": "Replaced the filter."},
        format="json",
    )
    assert response.status_code == 201

    listed = admin_client.get(TASKS).json()
    assert listed[0]["proofs"][0]["content"] == "Replaced the filter."


def test_staff_cannot_create_tasks(staff_client):
    assert staff_client.post(TASKS, task_payload(), format="json").status_code == 403
