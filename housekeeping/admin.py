"""housekeeping/admin.py — Phase 7"""
from django.contrib import admin
from housekeeping.models import RoomCleaning

@admin.register(RoomCleaning)
class RoomCleaningAdmin(admin.ModelAdmin):
    list_display = ["id", "hotel", "room", "assigned_to", "status", "created_at"]
    list_filter = ["hotel", "status"]
    list_select_related = ["hotel", "room", "assigned_to__user"]
