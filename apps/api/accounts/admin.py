from django.contrib import admin

from .models import Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan_tier", "status", "seat_limit", "created_at")
    search_fields = ("name", "slug")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "role", "tenant", "is_clocked_in")
    list_filter = ("role",)
    search_fields = ("email", "first_name", "last_name")
    exclude = ("password",)
