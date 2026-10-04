from django.contrib import admin

from .models import Task, TaskProof


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "field_staff", "due_at", "tenant")
    list_filter = ("status",)


admin.site.register(TaskProof)
