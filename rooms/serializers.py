"""
rooms/serializers.py
====================
المسار: rooms/serializers.py
Phase: 4 — Master Data

⚠️ N+1 Prevention:
   - RoomTypeSerializer → nested translations (prefetch_related في Selector)
   - RoomSerializer → select_related("room_type") في Selector
   - لا nested serializer عميق بدون prefetch مناسب
"""

from rest_framework import serializers
from rooms.models import Language, HotelLanguage, BookingSource, RoomType, RoomTypeTranslation, Room


# ---------------------------------------------------------------------------
# Language Serializers
# ---------------------------------------------------------------------------

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "code", "name", "native_name", "is_rtl", "is_active"]
        read_only_fields = ["id"]


class HotelLanguageSerializer(serializers.ModelSerializer):
    language_code = serializers.CharField(source="language.code", read_only=True)
    language_name = serializers.CharField(source="language.name", read_only=True)
    is_rtl = serializers.BooleanField(source="language.is_rtl", read_only=True)

    class Meta:
        model = HotelLanguage
        fields = ["id", "language", "language_code", "language_name", "is_rtl", "is_default"]
        read_only_fields = ["id", "language_code", "language_name", "is_rtl"]


class HotelLanguageWriteSerializer(serializers.Serializer):
    """Serializer للإضافة عبر language_code."""
    language_code = serializers.CharField(max_length=10)
    is_default = serializers.BooleanField(default=False)


# ---------------------------------------------------------------------------
# BookingSource Serializers
# ---------------------------------------------------------------------------

class BookingSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingSource
        fields = [
            "id", "name", "description", "is_online",
            "commission_rate", "is_active", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


# ---------------------------------------------------------------------------
# RoomType Serializers
# ---------------------------------------------------------------------------

class RoomTypeTranslationSerializer(serializers.ModelSerializer):
    language_code = serializers.CharField(source="language.code", read_only=True)

    class Meta:
        model = RoomTypeTranslation
        fields = ["id", "language", "language_code", "name", "description"]
        read_only_fields = ["id", "language_code"]


class RoomTypeSerializer(serializers.ModelSerializer):
    """
    ⚠️ N+1 Safe: translations field يفترض أن RoomType.translations
       مُجلَبَة مسبقاً بـ prefetch_related("translations__language") في Selector.
    """
    translations = RoomTypeTranslationSerializer(many=True, read_only=True)
    room_count = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            "id", "code", "base_price", "max_occupancy",
            "amenities", "sort_order", "is_active",
            "translations", "room_count", "created_at"
        ]
        read_only_fields = ["id", "translations", "room_count", "created_at"]

    def get_room_count(self, obj) -> int:
        """
        ⚠️ هذا سيعمل N+1 إلا لو استخدمنا annotate(Count("rooms")) في Selector.
           في Phase 4 نتركه بسيطاً ونُحسّنه بالـ annotate إذا احتاج التطبيق.
        """
        return obj.rooms.filter(is_active=True).count()


class RoomTypeWriteSerializer(serializers.ModelSerializer):
    """Serializer للكتابة فقط (Create/Update) بدون nested read-only fields."""
    translations = serializers.ListField(child=serializers.DictField(), required=False)

    class Meta:
        model = RoomType
        fields = ["code", "base_price", "max_occupancy", "amenities", "sort_order", "translations"]


# ---------------------------------------------------------------------------
# Room Serializers
# ---------------------------------------------------------------------------

class RoomSerializer(serializers.ModelSerializer):
    """
    ⚠️ N+1 Safe: room_type_code يقرأ من الـ FK الذي يجب أن يكون
       مُجلَباً بـ select_related("room_type") في Selector.
    """
    room_type_code = serializers.CharField(source="room_type.code", read_only=True)
    room_type_price = serializers.DecimalField(
        source="room_type.base_price", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Room
        fields = [
            "id", "room_number", "floor", "status",
            "room_type", "room_type_code", "room_type_price",
            "notes", "is_active", "created_at"
        ]
        read_only_fields = ["id", "room_type_code", "room_type_price", "created_at"]


class RoomWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["room_type", "room_number", "floor", "status", "notes"]

    def validate_room_type(self, value):
        """التأكد من أن room_type ينتمي لنفس الفندق."""
        hotel = self.context.get("hotel")
        if hotel and value.hotel_id != hotel.id:
            raise serializers.ValidationError("Room type does not belong to this hotel.")
        return value


class RoomStatusUpdateSerializer(serializers.Serializer):
    """تحديث حالة غرفة فقط."""
    status = serializers.ChoiceField(choices=[
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("maintenance", "Under Maintenance"),
        ("cleaning", "Being Cleaned"),
        ("inspecting", "Being Inspected"),
        ("out_of_order", "Out of Order"),
    ])
