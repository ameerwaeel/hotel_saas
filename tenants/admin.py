"""
tenants/admin.py
=================
المسار: tenants/admin.py
الوظيفة: Django Admin configuration لـ Hotel و HotelSettings.
"""

from django.contrib import admin
from .models import Hotel, HotelSettings


class HotelSettingsInline(admin.StackedInline):
    """HotelSettings تظهر inline مع Hotel في الـ admin."""
    model = HotelSettings
    can_delete = False
    verbose_name_plural = "Hotel Settings"
    extra = 1


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ["name", "subdomain", "status", "is_active", "default_currency", "created_at"]
    list_filter = ["status", "is_active", "default_currency", "default_language"]
    search_fields = ["name", "subdomain", "email"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [HotelSettingsInline]
    ordering = ["name"]


@admin.register(HotelSettings)
class HotelSettingsAdmin(admin.ModelAdmin):
    list_display = ["hotel", "checkin_time", "checkout_time", "allow_overbooking"]
    readonly_fields = ["id", "created_at", "updated_at"]
