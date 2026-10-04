"""
maintenance/serializers.py — Phase 7
"""
from rest_framework import serializers
from maintenance.models import RoomIssue


class RoomIssueSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    has_blocking_flag = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = RoomIssue
        fields = [
            "id", "room", "room_number", "title", "description",
            "status", "priority", "blocking",
            "assigned_to", "assigned_to_name",
            "resolved_at", "notes", "has_blocking_flag", "created_at"
        ]
        read_only_fields = ["id", "room_number", "assigned_to_name", "resolved_at", "created_at"]

    def get_assigned_to_name(self, obj) -> str:
        return obj.assigned_to.full_name if obj.assigned_to else ""


class RoomIssueCreateSerializer(serializers.Serializer):
    room = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=["low", "medium", "high", "critical"], default="medium")
    blocking = serializers.BooleanField(default=False)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)
