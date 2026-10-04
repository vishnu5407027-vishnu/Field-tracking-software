import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class PlanTier(models.TextChoices):
    BASIC = "BASIC"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class TenantStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PAST_DUE = "PAST_DUE"


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    DISPATCHER = "DISPATCHER"
    FIELD_STAFF = "FIELD_STAFF"


#: Roles that can be granted within a tenant (SUPER_ADMIN is platform-only).
TENANT_ROLES = (Role.TENANT_ADMIN, Role.DISPATCHER, Role.FIELD_STAFF)


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60, unique=True)
    plan_tier = models.CharField(max_length=20, choices=PlanTier, default=PlanTier.BASIC)
    status = models.CharField(
        max_length=20, choices=TenantStatus, default=TenantStatus.ACTIVE, db_index=True
    )
    seat_limit = models.PositiveIntegerField(default=5)
    razorpay_customer_id = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra):
        extra.setdefault("role", Role.SUPER_ADMIN)
        extra.setdefault("is_superuser", True)
        extra.setdefault("first_name", "Platform")
        extra.setdefault("last_name", "Owner")
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Null tenant = platform owner (SUPER_ADMIN) — they belong to no tenant.
    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.CASCADE, related_name="users"
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    role = models.CharField(max_length=20, choices=Role, default=Role.FIELD_STAFF)
    is_clocked_in = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        indexes = [
            models.Index(fields=["tenant"]),
            models.Index(fields=["tenant", "role"]),
        ]

    @property
    def is_staff(self) -> bool:  # Django admin access
        return self.is_superuser

    def __str__(self) -> str:
        return self.email
