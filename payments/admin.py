"""payments/admin.py — Phase 6"""
from django.contrib import admin
from payments.models import PaymentMethod, Payment

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["name", "hotel", "type", "is_active"]
    list_filter = ["hotel", "type", "is_active"]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "hotel", "amount", "currency", "method", "payment_date", "status"]
    list_filter = ["hotel", "status", "currency", "payment_date"]
    search_fields = ["reference"]
    list_select_related = ["hotel", "method", "reservation"]
    readonly_fields = ["created_at", "updated_at"]
