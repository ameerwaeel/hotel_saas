"""
reservations/admin.py
=====================
المسار: reservations/admin.py
Phase: 5 — Reservations
"""

from django.contrib import admin
from reservations.models import Reservation, ReservationRoom, ReservationRoomChange


class ReservationRoomInline(admin.TabularInline):
    model = ReservationRoom
    extra = 0
    readonly_fields = ["nightly_price", "nights", "created_at"]
    fields = ["room", "room_type", "check_in", "check_out", "nightly_price", "nights", "adults", "children"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        "id", "hotel", "customer", "status", "check_in", "check_out",
        "total_price", "currency", "created_at"
    ]
    list_filter = ["hotel", "status", "check_in"]
    search_fields = ["customer__first_name", "customer__last_name", "customer__phone"]
    list_select_related = ["hotel", "customer", "booking_source"]
    inlines = [ReservationRoomInline]
    readonly_fields = ["total_price", "created_at", "updated_at"]


@admin.register(ReservationRoom)
class ReservationRoomAdmin(admin.ModelAdmin):
    list_display = ["id", "reservation", "room", "check_in", "check_out", "nightly_price", "nights"]
    list_filter = ["hotel", "reservation__status"]
    list_select_related = ["reservation", "room", "room_type"]


@admin.register(ReservationRoomChange)
class ReservationRoomChangeAdmin(admin.ModelAdmin):
    list_display = ["reservation_room", "old_room", "new_room", "price_difference", "changed_by", "changed_at"]
    list_filter = ["changed_at"]
    readonly_fields = ["changed_at"]
