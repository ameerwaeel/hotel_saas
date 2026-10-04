"""
customers/admin.py
==================
المسار: customers/admin.py
Phase: 4 — Master Data
"""

from django.contrib import admin
from customers.models import Customer, Employee


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "hotel", "phone", "email", "vip_status", "total_stays", "is_active"]
    list_filter = ["hotel", "vip_status", "nationality", "is_active"]
    search_fields = ["first_name", "last_name", "phone", "email", "id_number"]
    list_select_related = ["hotel"]
    readonly_fields = ["total_stays", "created_at", "updated_at"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["full_name", "hotel", "position", "department", "is_active"]
    list_filter = ["hotel", "department", "is_active"]
    search_fields = ["user__email", "user__first_name", "employee_id"]
    list_select_related = ["hotel", "user"]
