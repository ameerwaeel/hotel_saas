"""
tenants/serializers.py
========================
المسار: tenants/serializers.py
الوظيفة: Serializers لـ Hotel و HotelSettings.
"""

from rest_framework import serializers
from .models import Hotel, HotelSettings


class HotelSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelSettings
        fields = [
            "checkin_time", "checkout_time", "exchange_rate_mode",
            "allow_overbooking", "max_advance_booking_days",
            "auto_close_daily", "invoice_prefix",
        ]


class HotelSerializer(serializers.ModelSerializer):
    """
    Serializer لعرض Hotel مع settings كـ nested object.
    ⚠️ select_related("settings") مطلوب في الـ view لتفادي N+1.
    """

    settings = HotelSettingsSerializer(read_only=True)
    is_operational = serializers.BooleanField(read_only=True)

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "slug", "subdomain", "email", "phone",
            "address", "city", "country", "timezone",
            "default_currency", "default_language",
            "status", "is_active", "is_operational",
            "logo", "settings", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "slug"]


class HotelCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء Hotel جديد."""

    class Meta:
        model = Hotel
        fields = [
            "name", "slug", "subdomain", "email", "phone",
            "address", "city", "country", "timezone",
            "default_currency", "default_language",
        ]

    def validate_subdomain(self, value):
        if Hotel.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError("This subdomain is already taken.")
        return value.lower()
