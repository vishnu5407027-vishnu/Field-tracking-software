import pytest
from rest_framework.test import APIClient

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

ME = "/api/v1/me"
PW = "/api/v1/me/password"


def test_get_own_profile(staff_client, staff):
    body = staff_client.get(ME).json()
    assert body["email"] == staff.email
    assert body["firstName"] == "Ravi"
    assert body["role"] == "FIELD_STAFF"
    assert body["tenantName"] == "Acme Field Services"


def test_update_profile_name_and_email(admin_client, admin):
    response = admin_client.patch(
        ME,
        {"firstName": "Asha", "lastName": "Menon", "email": "asha.menon@test.dev"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["lastName"] == "Menon"

    admin.refresh_from_db()
    assert admin.last_name == "Menon"
    assert admin.email == "asha.menon@test.dev"


def test_cannot_take_another_users_email(admin_client, staff):
    response = admin_client.patch(
        ME,
        {"firstName": "Asha", "lastName": "Nair", "email": staff.email},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.json()


def test_change_password_requires_correct_current(staff_client):
    assert staff_client.post(
        PW, {"currentPassword": "wrong-one", "newPassword": "BrandNew123!"}, format="json"
    ).status_code == 400


def test_change_password_then_login_with_new(staff_client, staff):
    response = staff_client.post(
        PW, {"currentPassword": PASSWORD, "newPassword": "BrandNew123!"}, format="json"
    )
    assert response.status_code == 200

    fresh = APIClient()
    assert fresh.post(
        "/api/v1/auth/login",
        {"email": staff.email, "password": "BrandNew123!"},
        format="json",
    ).status_code == 200
    assert fresh.post(
        "/api/v1/auth/login",
        {"email": staff.email, "password": PASSWORD},
        format="json",
    ).status_code == 401


def test_profile_requires_auth():
    assert APIClient().get(ME).status_code == 401
