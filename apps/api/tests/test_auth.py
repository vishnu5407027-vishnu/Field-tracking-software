import pytest
from rest_framework.test import APIClient

from accounts.models import TenantStatus

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"


def test_login_returns_camelcase_session(admin):
    response = APIClient().post(
        LOGIN, {"email": admin.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accessToken"]
    assert body["user"]["firstName"] == "Asha"
    assert body["user"]["role"] == "TENANT_ADMIN"
    assert body["user"]["tenantName"] == "Acme Field Services"


def test_login_rejects_wrong_password(admin):
    response = APIClient().post(
        LOGIN, {"email": admin.email, "password": "wrong-password"}, format="json"
    )
    assert response.status_code == 401


def test_login_blocked_for_suspended_tenant(admin, tenant):
    tenant.status = TenantStatus.SUSPENDED
    tenant.save()
    response = APIClient().post(
        LOGIN, {"email": admin.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 403


def test_requests_without_token_are_rejected():
    assert APIClient().get("/api/v1/users").status_code == 401
