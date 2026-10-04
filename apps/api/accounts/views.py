from django.contrib.auth.hashers import check_password
from django.db import models
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.jwt import issue_tokens
from core.permissions import HasRole

from .models import Role, Tenant, TenantStatus, User
from .serializers import (
    AdminSetPasswordSerializer,
    AdminUpdateUserSerializer,
    ChangePasswordSerializer,
    CreateTenantSerializer,
    InviteUserSerializer,
    LoginSerializer,
    MemberSerializer,
    ProfileSerializer,
    SessionUserSerializer,
    TenantSerializer,
    UpdateProfileSerializer,
    UpdateRoleSerializer,
    UpdateTenantStatusSerializer,
    field_staff_count_queryset,
)

# Monthly price per field-staff seat, in INR — used for the MRR metric.
SEAT_PRICE_INR = {"BASIC": 299, "PRO": 599, "ENTERPRISE": 999}


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer  # OpenAPI hint

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = (
            User.objects.select_related("tenant")
            .filter(email__iexact=data["email"], is_active=True)
            .first()
        )
        if user is None or not check_password(data["password"], user.password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if user.tenant and user.tenant.status == TenantStatus.SUSPENDED:
            return Response(
                {"detail": "This account has been suspended"}, status=status.HTTP_403_FORBIDDEN
            )

        tokens = issue_tokens(user)
        return Response(
            {
                "access_token": tokens["access"],
                "refresh_token": tokens["refresh"],
                "user": SessionUserSerializer(user).data,
            }
        )


# ── Self-service profile (any authenticated user) ──────────────────────────


class MeView(APIView):
    """Read or update the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer  # OpenAPI hint

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.first_name = serializer.validated_data["first_name"]
        user.last_name = serializer.validated_data["last_name"]
        user.email = serializer.validated_data["email"]
        user.save(update_fields=["first_name", "last_name", "email"])
        return Response(ProfileSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer  # OpenAPI hint

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"detail": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated"})


# ── Tenant team management ─────────────────────────────────────────────────


class UsersView(APIView):
    permission_classes = [HasRole]
    allowed_roles_by_method = {
        "GET": (Role.TENANT_ADMIN, Role.DISPATCHER),
        "POST": (Role.TENANT_ADMIN,),
    }
    serializer_class = MemberSerializer  # OpenAPI hint

    def get(self, request):
        members = User.objects.filter(tenant_id=request.user.tenant_id).order_by("created_at")
        return Response(MemberSerializer(members, many=True).data)

    def post(self, request):
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(email__iexact=data["email"]).exists():
            return Response(
                {"detail": "Email already registered"}, status=status.HTTP_409_CONFLICT
            )

        if data["role"] == Role.FIELD_STAFF:
            tenant = Tenant.objects.get(pk=request.user.tenant_id)
            used = User.objects.filter(tenant=tenant, role=Role.FIELD_STAFF).count()
            if used >= tenant.seat_limit:
                raise PermissionDenied(
                    f"Field staff seat limit ({tenant.seat_limit}) reached — "
                    "upgrade the plan to add more"
                )

        user = User.objects.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=data["role"],
            tenant_id=request.user.tenant_id,
        )
        return Response(MemberSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.TENANT_ADMIN,)
    serializer_class = MemberSerializer  # OpenAPI hint

    def get_member(self, request, pk) -> User:
        member = User.objects.filter(pk=pk, tenant_id=request.user.tenant_id).first()
        if member is None:
            raise NotFound("User not found")
        return member

    def patch(self, request, pk):
        """Admin updates a member's profile (name + email)."""
        member = self.get_member(request, pk)
        serializer = AdminUpdateUserSerializer(
            data=request.data, context={"target_id": member.pk}
        )
        serializer.is_valid(raise_exception=True)
        member.first_name = serializer.validated_data["first_name"]
        member.last_name = serializer.validated_data["last_name"]
        member.email = serializer.validated_data["email"]
        member.save(update_fields=["first_name", "last_name", "email"])
        return Response(MemberSerializer(member).data)

    def delete(self, request, pk):
        member = self.get_member(request, pk)
        if member.pk == request.user.pk:
            raise PermissionDenied("Cannot delete yourself")
        member.delete()
        return Response({"deleted": True})


class UserPasswordView(UserDetailView):
    """Admin resets any member's password (including their own)."""

    serializer_class = AdminSetPasswordSerializer  # OpenAPI hint

    def post(self, request, pk):
        member = self.get_member(request, pk)
        serializer = AdminSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member.set_password(serializer.validated_data["new_password"])
        member.save(update_fields=["password"])
        return Response({"detail": "Password updated"})


class UserRoleView(UserDetailView):
    def patch(self, request, pk):
        member = self.get_member(request, pk)
        if member.pk == request.user.pk:
            raise PermissionDenied("Cannot change your own role")
        serializer = UpdateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member.role = serializer.validated_data["role"]
        member.save(update_fields=["role"])
        return Response({"id": member.id, "email": member.email, "role": member.role})


# ── Owner portal (platform-level, no tenant scoping) ───────────────────────


class OwnerAnalyticsView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.SUPER_ADMIN,)

    def get(self, request):
        tenants_by_status = dict(
            Tenant.objects.values_list("status").annotate(n=models.Count("id"))
        )
        field_staff = User.objects.filter(role=Role.FIELD_STAFF)
        mrr_inr = sum(
            SEAT_PRICE_INR[t.plan_tier] * t.seat_limit
            for t in Tenant.objects.filter(status=TenantStatus.ACTIVE).only(
                "plan_tier", "seat_limit"
            )
        )
        return Response(
            {
                "tenants_by_status": tenants_by_status,
                "total_field_staff": field_staff.count(),
                "online_field_staff": field_staff.filter(is_clocked_in=True).count(),
                "mrr_inr": mrr_inr,
            }
        )


class OwnerTenantsView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.SUPER_ADMIN,)
    serializer_class = TenantSerializer  # OpenAPI hint

    def get(self, request):
        return Response(TenantSerializer(field_staff_count_queryset(), many=True).data)

    def post(self, request):
        serializer = CreateTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant = Tenant.objects.create(
            name=data["name"],
            slug=data["slug"],
            plan_tier=data["plan_tier"],
            seat_limit=data["seat_limit"],
        )
        User.objects.create_user(
            email=data["admin_email"],
            password=data["admin_password"],
            first_name=data["admin_first_name"],
            last_name=data["admin_last_name"],
            role=Role.TENANT_ADMIN,
            tenant=tenant,
        )
        tenant.field_staff_count = 0
        return Response(TenantSerializer(tenant).data, status=status.HTTP_201_CREATED)


class OwnerTenantDetailView(APIView):
    permission_classes = [HasRole]
    allowed_roles = (Role.SUPER_ADMIN,)
    serializer_class = TenantSerializer  # OpenAPI hint

    def get_tenant(self, pk) -> Tenant:
        tenant = Tenant.objects.filter(pk=pk).first()
        if tenant is None:
            raise NotFound("Tenant not found")
        return tenant

    def delete(self, request, pk):
        self.get_tenant(pk).delete()  # cascades to users, tasks, logs
        return Response({"deleted": True})


class OwnerTenantStatusView(OwnerTenantDetailView):
    def patch(self, request, pk):
        tenant = self.get_tenant(pk)
        serializer = UpdateTenantStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant.status = serializer.validated_data["status"]
        tenant.save(update_fields=["status", "updated_at"])
        tenant.field_staff_count = User.objects.filter(
            tenant=tenant, role=Role.FIELD_STAFF
        ).count()
        return Response(TenantSerializer(tenant).data)
