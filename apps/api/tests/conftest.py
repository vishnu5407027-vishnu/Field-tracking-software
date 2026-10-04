import fakeredis
import pytest
from rest_framework.test import APIClient

from accounts.models import PlanTier, Role, Tenant, User
from core import live

PASSWORD = "Password123!"


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(live, "_client", client)
    return client


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Acme Field Services", slug="acme", plan_tier=PlanTier.PRO, seat_limit=2
    )


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="owner@test.dev", password=PASSWORD,
        first_name="Platform", last_name="Owner", role=Role.SUPER_ADMIN,
    )


@pytest.fixture
def admin(tenant):
    return User.objects.create_user(
        email="admin@test.dev", password=PASSWORD,
        first_name="Asha", last_name="Nair", role=Role.TENANT_ADMIN, tenant=tenant,
    )


@pytest.fixture
def staff(tenant):
    return User.objects.create_user(
        email="staff@test.dev", password=PASSWORD,
        first_name="Ravi", last_name="Kumar", role=Role.FIELD_STAFF, tenant=tenant,
    )


def client_for(user) -> APIClient:
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['accessToken']}")
    return client


@pytest.fixture
def owner_client(owner):
    return client_for(owner)


@pytest.fixture
def admin_client(admin):
    return client_for(admin)


@pytest.fixture
def staff_client(staff):
    return client_for(staff)
