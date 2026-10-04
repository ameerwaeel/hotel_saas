"""
reservations/serializers.py
============================
المسار: reservations/serializers.py
Phase: 5 — Reservations

⚠️ N+1 Prevention:
   ReservationSerializer → nested ReservationRoom → Room → RoomType
   كل مستوى يحتاج prefetch/select مناسب في Selector.
"""

from rest_framework import serializers
from reservations.models import Reservation, ReservationRoom, ReservationRoomChange


# ---------------------------------------------------------------------------
# ReservationRoom Serializers
# ---------------------------------------------------------------------------

class ReservationRoomSerializer(serializers.ModelSerializer):
    """
    ⚠️ N+1 Safe: room_number/room_type_code يقرأن من FKs مُجلَبة مسبقاً
       بـ select_related("room__room_type") في Selector.
    """
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    room_type_code = serializers.CharField(source="room_type.code", read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ReservationRoom
        fields = [
            "id", "room", "room_number", "room_type", "room_type_code",
            "check_in", "check_out", "nightly_price", "nights",
            "total_price", "adults", "children", "notes"
        ]
        read_only_fields = [
            "id", "room_number", "room_type_code", "nightly_price",
            "nights", "total_price"
        ]


class ReservationRoomChangeSerializer(serializers.ModelSerializer):
    old_room_number = serializers.CharField(source="old_room.room_number", read_only=True)
    new_room_number = serializers.CharField(source="new_room.room_number", read_only=True)
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True)

    class Meta:
        model = ReservationRoomChange
        fields = [
            "id", "old_room", "old_room_number", "new_room", "new_room_number",
            "old_price", "new_price", "price_difference", "reason",
            "changed_by", "changed_by_name", "changed_at"
        ]
        read_only_fields = ["id", "changed_at"]


# ---------------------------------------------------------------------------
# Reservation Serializers
# ---------------------------------------------------------------------------

class ReservationSerializer(serializers.ModelSerializer):
    """
    ⚠️ N+1 Safe — requires:
       select_related("customer", "booking_source", "created_by")
       prefetch_related("reservation_rooms__room__room_type")
    """
    reservation_rooms = ReservationRoomSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    booking_source_name = serializers.CharField(
        source="booking_source.name", read_only=True, default=None
    )
    nights = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "customer", "customer_name", "booking_source", "booking_source_name",
            "status", "check_in", "check_out", "nights",
            "adults", "children", "total_price", "currency",
            "special_requests", "internal_notes",
            "confirmed_at", "checked_in_at", "checked_out_at",
            "cancelled_at", "cancellation_reason",
            "created_by", "created_by_name", "created_at",
            "reservation_rooms",
        ]
        read_only_fields = [
            "id", "status", "total_price", "nights",
            "confirmed_at", "checked_in_at", "checked_out_at",
            "cancelled_at", "created_at", "customer_name",
            "booking_source_name", "created_by_name", "reservation_rooms"
        ]


class ReservationCreateSerializer(serializers.Serializer):
    """Serializer لإنشاء حجز جديد — يُمرَّر للـ ReservationService."""
    customer = serializers.UUIDField()
    booking_source = serializers.UUIDField(required=False, allow_null=True)
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    adults = serializers.IntegerField(default=1, min_value=1)
    children = serializers.IntegerField(default=0, min_value=0)
    currency = serializers.CharField(max_length=3, default="USD")
    special_requests = serializers.CharField(required=False, allow_blank=True, default="")
    internal_notes = serializers.CharField(required=False, allow_blank=True, default="")
    rooms = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )

    def validate(self, data):
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError(
                {"check_out": "Check-out must be after check-in."}
            )
        return data


class ReservationStatusUpdateSerializer(serializers.Serializer):
    """تحديث حالة الحجز مع سبب اختياري."""
    action = serializers.ChoiceField(choices=[
        "confirm", "cancel", "check_in", "check_out", "no_show"
    ])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RoomUpgradeSerializer(serializers.Serializer):
    """ترقية/تغيير غرفة داخل حجز."""
    reservation_room_id = serializers.UUIDField()
    new_room_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AvailabilityQuerySerializer(serializers.Serializer):
    """Query params للـ availability check."""
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    room_type_id = serializers.UUIDField(required=False)

    def validate(self, data):
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError(
                {"check_out": "Check-out must be after check-in."}
            )
        return data
