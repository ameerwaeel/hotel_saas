"""
rooms/admin.py
==============
المسار: rooms/admin.py
Phase: 4 — Master Data
"""

from django.contrib import admin
from rooms.models import Language, HotelLanguage, BookingSource, RoomType, RoomTypeTranslation, Room


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "native_name", "is_rtl", "is_active"]
    list_filter = ["is_rtl", "is_active"]
    search_fields = ["code", "name"]


class RoomTypeTranslationInline(admin.TabularInline):
    model = RoomTypeTranslation
    extra = 1


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "hotel", "base_price", "max_occupancy", "sort_order", "is_active"]
    list_filter = ["hotel", "is_active"]
    search_fields = ["code"]
    inlines = [RoomTypeTranslationInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["room_number", "hotel", "room_type", "floor", "status", "is_active"]
    list_filter = ["hotel", "status", "floor", "is_active"]
    search_fields = ["room_number"]
    list_select_related = ["hotel", "room_type"]


@admin.register(HotelLanguage)
class HotelLanguageAdmin(admin.ModelAdmin):
    list_display = ["hotel", "language", "is_default", "is_active"]
    list_filter = ["hotel", "is_default"]


@admin.register(BookingSource)
class BookingSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "hotel", "is_online", "commission_rate", "is_active"]
    list_filter = ["hotel", "is_online", "is_active"]
    search_fields = ["name"]
