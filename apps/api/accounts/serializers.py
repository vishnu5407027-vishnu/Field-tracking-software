from django.db import models
from rest_framework import serializers

from .models import PlanTier, Role, Tenant, TenantStatus, User, TENANT_ROLES


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, trim_whitespace=False)


class SessionUserSerializer(serializers.ModelSerializer):
    tenant_id = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "tenant_id", "tenant_name"]

    def get_tenant_id(self, user: User) -> str | None:
        return str(user.tenant_id) if user.tenant_id else None

    def get_tenant_name(self, user: User) -> str | None:
        return user.tenant.name if user.tenant_id else None


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "is_clocked_in", "created_at"]


class ProfileSerializer(serializers.ModelSerializer):
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "role",
            "is_clocked_in", "created_at", "tenant_name",
        ]

    def get_tenant_name(self, user: User) -> str | None:
        return user.tenant.name if user.tenant_id else None


class UpdateProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        user = self.context["request"].user
        if User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already in use")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(min_length=8, trim_whitespace=False)


class AdminUpdateUserSerializer(serializers.Serializer):
    """A tenant admin editing another member's profile."""

    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        # Uniqueness is checked against everyone except the member being edited.
        target_id = self.context["target_id"]
        if User.objects.exclude(pk=target_id).filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already in use")
        return value


class AdminSetPasswordSerializer(serializers.Serializer):
    """A tenant admin resetting a member's password (no current password)."""

    new_password = serializers.CharField(min_length=8, trim_whitespace=False)


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, trim_whitespace=False)
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    role = serializers.ChoiceField(choices=[(r.value, r.value) for r in TENANT_ROLES])


class UpdateRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[(r.value, r.value) for r in TENANT_ROLES])


class TenantSerializer(serializers.ModelSerializer):
    field_staff_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "plan_tier", "status", "seat_limit",
            "created_at", "field_staff_count",
        ]


class CreateTenantSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=120)
    slug = serializers.SlugField(max_length=60)
    plan_tier = serializers.ChoiceField(choices=PlanTier.choices)
    seat_limit = serializers.IntegerField(min_value=1, required=False, default=5)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8, trim_whitespace=False)
    admin_first_name = serializers.CharField(max_length=60)
    admin_last_name = serializers.CharField(max_length=60)

    def validate_slug(self, value: str) -> str:
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Slug already in use")
        return value

    def validate_admin_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value


class UpdateTenantStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TenantStatus.choices)


def field_staff_count_queryset() -> models.QuerySet[Tenant]:
    return Tenant.objects.annotate(
        field_staff_count=models.Count("users", filter=models.Q(users__role=Role.FIELD_STAFF))
    ).order_by("-created_at")
