import io
from datetime import datetime, timedelta, timezone

import pytest

from fieldtasks.models import Task, TaskStatus

pytestmark = pytest.mark.django_db

TASKS = "/api/v1/tasks"


def make_task(admin, staff, **overrides):
    data = dict(
        tenant=staff.tenant,
        title="AC inspection",
        lat=8.5566,
        lng=76.8810,
        address="Technopark",
        dispatcher=admin,
        field_staff=staff,
        due_at=datetime(2026, 6, 13, 9, 0, tzinfo=timezone.utc),
        status=TaskStatus.ASSIGNED,
    )
    data.update(overrides)
    return Task.objects.create(**data)


def test_task_detail_for_dispatcher(admin_client, admin, staff):
    task = make_task(admin, staff)
    body = admin_client.get(f"{TASKS}/{task.id}").json()
    assert body["title"] == "AC inspection"
    assert body["fieldStaff"]["firstName"] == "Ravi"
    assert "startedAt" in body


def test_en_route_stamps_started_at(staff_client, admin, staff):
    task = make_task(admin, staff)
    staff_client.patch(
        f"/api/v1/staff/tasks/{task.id}", {"status": "EN_ROUTE"}, format="json"
    )
    task.refresh_from_db()
    assert task.started_at is not None


def test_route_returns_points_and_live(admin_client, staff_client, admin, staff, fake_redis):
    task = make_task(admin, staff)
    # Worker goes en route; backdate started_at so the pings fall in-window.
    staff_client.patch(
        f"/api/v1/staff/tasks/{task.id}", {"status": "EN_ROUTE"}, format="json"
    )
    task.refresh_from_db()
    task.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    task.save(update_fields=["started_at"])

    now = datetime.now(timezone.utc)
    pings = [
        {"lat": 8.551, "lng": 76.880, "recordedAt": (now - timedelta(minutes=5)).isoformat()},
        {"lat": 8.553, "lng": 76.881, "recordedAt": (now - timedelta(minutes=2)).isoformat()},
    ]
    staff_client.post("/api/v1/staff/locations", {"pings": pings}, format="json")

    body = admin_client.get(f"{TASKS}/{task.id}/route").json()
    assert body["destination"] == {"lat": 8.5566, "lng": 76.8810}
    assert len(body["points"]) >= 2
    assert body["live"] is not None and body["live"]["userId"] == str(staff.id)


def test_completed_task_history_no_live(admin_client, staff_client, admin, staff, fake_redis):
    task = make_task(admin, staff)
    staff_client.patch(f"/api/v1/staff/tasks/{task.id}", {"status": "EN_ROUTE"}, format="json")
    staff_client.patch(f"/api/v1/staff/tasks/{task.id}", {"status": "COMPLETED"}, format="json")
    body = admin_client.get(f"{TASKS}/{task.id}/route").json()
    assert body["status"] == "COMPLETED"
    assert body["live"] is None


def test_completed_tasks_listing_for_staff(staff_client, admin, staff):
    make_task(admin, staff, title="Open one")
    done = make_task(admin, staff, title="Done one", status=TaskStatus.COMPLETED,
                     completed_at=datetime.now(timezone.utc))

    open_titles = [t["title"] for t in staff_client.get("/api/v1/staff/tasks").json()]
    assert "Open one" in open_titles and "Done one" not in open_titles

    done_titles = [t["title"] for t in staff_client.get("/api/v1/staff/tasks?completed=1").json()]
    assert done_titles == ["Done one"]
    assert str(done.id) in [t["id"] for t in
                            staff_client.get("/api/v1/staff/tasks?completed=1").json()]


def test_photo_upload_creates_proof(staff_client, admin, staff, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    task = make_task(admin, staff)
    png = io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimage")
    png.name = "shot.png"

    response = staff_client.post(
        f"/api/v1/staff/tasks/{task.id}/photo", {"photo": png}, format="multipart"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "PHOTO"
    assert body["content"].startswith("/media/proofs/")

    detail = staff_client.get(f"/api/v1/staff/tasks/{task.id}").json()
    assert any(p["type"] == "PHOTO" for p in detail["proofs"])
