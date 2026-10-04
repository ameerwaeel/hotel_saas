"""
payments/serializers.py + finance/serializers.py
"""
from rest_framework import serializers
from payments.models import PaymentMethod, Payment


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "type", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(source="method.name", read_only=True)
    customer_name = serializers.SerializerMethodField()
    reservation_ref = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "reservation", "reservation_ref",
            "amount", "currency", "method", "method_name",
            "payment_date", "reference", "status", "notes",
            "processed_by", "customer_name",
            "created_at",
        ]
        read_only_fields = ["id", "method_name", "customer_name", "reservation_ref", "created_at"]

    def get_customer_name(self, obj) -> str:
        if obj.reservation and obj.reservation.customer:
            return obj.reservation.customer.full_name
        return ""

    def get_reservation_ref(self, obj) -> str:
        if obj.reservation:
            return str(obj.reservation_id)[:8]
        return ""


class PaymentCreateSerializer(serializers.Serializer):
    reservation = serializers.UUIDField(required=False, allow_null=True)
    method = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=3, default="USD")
    payment_date = serializers.DateField()
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
