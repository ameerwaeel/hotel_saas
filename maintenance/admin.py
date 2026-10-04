"""maintenance/admin.py — Phase 7"""
from django.contrib import admin
from maintenance.models import RoomIssue

@admin.register(RoomIssue)
class RoomIssueAdmin(admin.ModelAdmin):
    list_display = ["title", "hotel", "room", "status", "priority", "blocking", "created_at"]
    list_filter = ["hotel", "status", "priority", "blocking"]
    search_fields = ["title", "room__room_number"]
    list_select_related = ["hotel", "room", "assigned_to__user"]
