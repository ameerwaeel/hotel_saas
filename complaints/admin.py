"""complaints/admin.py — Phase 7"""
from django.contrib import admin
from complaints.models import CustomerComplaint

@admin.register(CustomerComplaint)
class CustomerComplaintAdmin(admin.ModelAdmin):
    list_display = ["title", "hotel", "customer", "status", "priority", "created_at"]
    list_filter = ["hotel", "status", "priority", "category"]
    search_fields = ["title", "customer__first_name", "customer__last_name"]
    list_select_related = ["hotel", "customer", "assigned_to__user"]
