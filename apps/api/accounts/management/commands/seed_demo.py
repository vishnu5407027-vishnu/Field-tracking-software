"""Idempotent demo data: a platform owner, one tenant with a full team,
a geofence, and an assigned task. Safe to run on every container start."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import PlanTier, Role, Tenant, User
from fieldtasks.models import Task, TaskStatus
from tracking.models import Geofence

PASSWORD = "Password123!"


class Command(BaseCommand):
    help = "Seed demo tenant, users, geofence, and task"

    def handle(self, *args, **options):
        def ensure_user(email, first, last, role, tenant=None):
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=PASSWORD,
                    first_name=first,
                    last_name=last,
                    role=role,
                    tenant=tenant,
                )
            return user

        ensure_user("owner@fieldtracking.dev", "Platform", "Owner", Role.SUPER_ADMIN)

        tenant, _ = Tenant.objects.get_or_create(
            slug="acme-services",
            defaults={"name": "Acme Field Services", "plan_tier": PlanTier.PRO, "seat_limit": 10},
        )

        admin = ensure_user("admin@acme.test", "Asha", "Nair", Role.TENANT_ADMIN, tenant)
        ensure_user("dispatch@acme.test", "Dev", "Menon", Role.DISPATCHER, tenant)
        staff1 = ensure_user("ravi@acme.test", "Ravi", "Kumar", Role.FIELD_STAFF, tenant)
        ensure_user("priya@acme.test", "Priya", "Sharma", Role.FIELD_STAFF, tenant)

        if not Geofence.objects.filter(tenant=tenant).exists():
            Geofence.objects.create(
                tenant=tenant,
                name="Client HQ — Technopark",
                lat=8.5566,
                lng=76.8810,
                radius_m=250,
            )
            Task.objects.create(
                tenant=tenant,
                title="AC unit inspection",
                description="Quarterly maintenance check, Block B, 3rd floor.",
                status=TaskStatus.ASSIGNED,
                lat=8.5566,
                lng=76.8810,
                address="Technopark Campus, Thiruvananthapuram",
                dispatcher=admin,
                field_staff=staff1,
                due_at=timezone.now() + timedelta(days=1),
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded. All passwords: {PASSWORD}"))
        for line in (
            "  owner@fieldtracking.dev  (SUPER_ADMIN)",
            "  admin@acme.test          (TENANT_ADMIN)",
            "  dispatch@acme.test       (DISPATCHER)",
            "  ravi@acme.test           (FIELD_STAFF)",
            "  priya@acme.test          (FIELD_STAFF)",
        ):
            self.stdout.write(line)
