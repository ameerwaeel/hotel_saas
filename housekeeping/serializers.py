"""
housekeeping/serializers.py — Phase 7
"""
from rest_framework import serializers
from housekeeping.models import RoomCleaning


class RoomCleaningSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = RoomCleaning
        fields = [
            "id", "room", "room_number", "assigned_to", "assigned_to_name",
            "reservation", "status", "started_at", "completed_at", "inspected_at",
            "notes", "created_at"
        ]
        read_only_fields = ["id", "room_number", "assigned_to_name", "created_at",
                            "started_at", "completed_at", "inspected_at"]

    def get_assigned_to_name(self, obj) -> str:
        return obj.assigned_to.full_name if obj.assigned_to else ""


class CleaningActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["start", "complete", "inspect"])
    employee_id = serializers.UUIDField(required=False)
