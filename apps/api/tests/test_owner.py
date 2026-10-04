import pytest
from rest_framework.test import APIClient

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

TENANTS = "/api/v1/owner/tenants"


def tenant_payload(slug="globex"):
    return {
        "name": "Globex Corp",
        "slug": slug,
        "planTier": "BASIC",
        "adminEmail": f"admin@{slug}.test",
        "adminPassword": PASSWORD,
        "adminFirstName": "Hank",
        "adminLastName": "Scorpio",
    }


def test_owner_analytics_shape(owner_client, tenant, staff):
    body = owner_client.get("/api/v1/owner/analytics").json()
    assert body["tenantsByStatus"] == {"ACTIVE": 1}
    assert body["totalFieldStaff"] == 1
    assert body["onlineFieldStaff"] == 0
    assert body["mrrInr"] == 599 * 2  # PRO seat price x seat_limit


def test_provision_tenant_and_admin_login(owner_client):
    response = owner_client.post(TENANTS, tenant_payload(), format="json")
    assert response.status_code == 201

    login = APIClient().post(
        "/api/v1/auth/login",
        {"email": "admin@globex.test", "password": PASSWORD},
        format="json",
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "TENANT_ADMIN"
    assert login.json()["user"]["tenantName"] == "Globex Corp"


def test_duplicate_slug_rejected(owner_client):
    owner_client.post(TENANTS, tenant_payload(), format="json")
    response = owner_client.post(TENANTS, tenant_payload(), format="json")
    assert response.status_code == 400


def test_suspend_tenant_blocks_member_login(owner_client, tenant, admin):
    response = owner_client.patch(
        f"{TENANTS}/{tenant.id}/status", {"status": "SUSPENDED"}, format="json"
    )
    assert response.status_code == 200

    login = APIClient().post(
        "/api/v1/auth/login", {"email": admin.email, "password": PASSWORD}, format="json"
    )
    assert login.status_code == 403


def test_tenant_admin_cannot_access_owner_portal(admin_client):
    assert admin_client.get("/api/v1/owner/analytics").status_code == 403
