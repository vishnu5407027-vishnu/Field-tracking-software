import pytest

pytestmark = pytest.mark.django_db

USERS = "/api/v1/users"


def invite_payload(email="new@test.dev", role="FIELD_STAFF"):
    return {
        "email": email,
        "password": "Password123!",
        "firstName": "New",
        "lastName": "Member",
        "role": role,
    }


def test_staff_cannot_list_team(staff_client):
    assert staff_client.get(USERS).status_code == 403


def test_admin_invites_member(admin_client):
    response = admin_client.post(USERS, invite_payload(), format="json")
    assert response.status_code == 201
    assert response.json()["isClockedIn"] is False

    members = admin_client.get(USERS).json()
    assert any(m["email"] == "new@test.dev" for m in members)


def test_duplicate_email_conflicts(admin_client, staff):
    response = admin_client.post(USERS, invite_payload(email=staff.email), format="json")
    assert response.status_code == 409


def test_field_staff_seat_limit_enforced(admin_client, staff, tenant):
    # seat_limit=2 in the fixture; `staff` occupies one seat.
    assert admin_client.post(
        USERS, invite_payload(email="second@test.dev"), format="json"
    ).status_code == 201
    response = admin_client.post(USERS, invite_payload(email="third@test.dev"), format="json")
    assert response.status_code == 403
    assert "seat limit" in response.json()["detail"]


def test_admin_cannot_delete_self(admin_client, admin):
    assert admin_client.delete(f"{USERS}/{admin.id}").status_code == 403


def test_admin_updates_member_role(admin_client, staff):
    response = admin_client.patch(
        f"{USERS}/{staff.id}/role", {"role": "DISPATCHER"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["role"] == "DISPATCHER"


def test_admin_updates_member_profile(admin_client, staff):
    response = admin_client.patch(
        f"{USERS}/{staff.id}",
        {"firstName": "Ravindra", "lastName": "K", "email": "ravindra@test.dev"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["firstName"] == "Ravindra"
    staff.refresh_from_db()
    assert staff.email == "ravindra@test.dev"


def test_admin_update_rejects_duplicate_email(admin_client, admin, staff):
    response = admin_client.patch(
        f"{USERS}/{staff.id}",
        {"firstName": "Ravi", "lastName": "Kumar", "email": admin.email},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.json()


def test_admin_resets_member_password(admin_client, staff):
    from rest_framework.test import APIClient

    response = admin_client.post(
        f"{USERS}/{staff.id}/password", {"newPassword": "ResetByAdmin1!"}, format="json"
    )
    assert response.status_code == 200

    login = APIClient().post(
        "/api/v1/auth/login",
        {"email": staff.email, "password": "ResetByAdmin1!"},
        format="json",
    )
    assert login.status_code == 200


def test_staff_cannot_edit_or_reset_others(staff_client, admin):
    assert staff_client.patch(
        f"{USERS}/{admin.id}",
        {"firstName": "X", "lastName": "Y", "email": "x@test.dev"},
        format="json",
    ).status_code == 403
    assert staff_client.post(
        f"{USERS}/{admin.id}/password", {"newPassword": "Hacker12345"}, format="json"
    ).status_code == 403


def test_admin_cannot_edit_user_in_another_tenant(admin_client, db):
    from accounts.models import PlanTier, Role, Tenant, User

    other = Tenant.objects.create(name="Other", slug="other", plan_tier=PlanTier.BASIC)
    outsider = User.objects.create_user(
        email="outsider@other.test", password="Password123!",
        first_name="Out", last_name="Sider", role=Role.FIELD_STAFF, tenant=other,
    )
    assert admin_client.patch(
        f"{USERS}/{outsider.id}",
        {"firstName": "Z", "lastName": "Z", "email": "z@test.dev"},
        format="json",
    ).status_code == 404
