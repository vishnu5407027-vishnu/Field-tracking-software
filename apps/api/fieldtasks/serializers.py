from rest_framework import serializers

from .models import ProofType, Task, TaskProof, TaskStatus


class TaskProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskProof
        fields = ["id", "task_id", "type", "content", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    field_staff = serializers.SerializerMethodField()
    proofs = TaskProofSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "status", "lat", "lng", "address",
            "dispatcher_id", "field_staff_id", "field_staff", "due_at",
            "started_at", "completed_at", "created_at", "proofs",
        ]

    def get_field_staff(self, task) -> dict | None:
        if task.field_staff_id is None:
            return None
        return {
            "id": str(task.field_staff.id),
            "first_name": task.field_staff.first_name,
            "last_name": task.field_staff.last_name,
        }


class CreateTaskSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=2, max_length=200)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    address = serializers.CharField(max_length=300)
    field_staff_id = serializers.UUIDField(required=False, allow_null=True)
    due_at = serializers.DateTimeField()


class UpdateTaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TaskStatus.choices)


class AddProofSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=ProofType.choices)
    content = serializers.CharField()
