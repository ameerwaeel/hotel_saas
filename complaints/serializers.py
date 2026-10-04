"""
complaints/serializers.py — Phase 7
"""
from rest_framework import serializers
from complaints.models import CustomerComplaint


class CustomerComplaintSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerComplaint
        fields = [
            "id", "customer", "customer_name", "reservation", "category",
            "title", "description", "status", "priority",
            "assigned_to", "assigned_to_name",
            "resolved_at", "resolution_notes", "created_at"
        ]
        read_only_fields = ["id", "customer_name", "assigned_to_name", "resolved_at", "created_at"]

    def get_assigned_to_name(self, obj) -> str:
        return obj.assigned_to.full_name if obj.assigned_to else ""


class ComplaintCreateSerializer(serializers.Serializer):
    customer = serializers.UUIDField()
    reservation = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_blank=True, default="")
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    priority = serializers.ChoiceField(choices=["low", "medium", "high"], default="medium")
    assigned_to = serializers.UUIDField(required=False, allow_null=True)
