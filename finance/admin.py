"""finance/admin.py — Phase 6"""
from django.contrib import admin
from finance.models import (
    FinanceCategory, FinancialTransaction, ExchangeRate,
    DailyClosing, MonthlyClosing
)

@admin.register(FinanceCategory)
class FinanceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "hotel", "type", "is_active"]
    list_filter = ["hotel", "type"]

@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "hotel", "type", "amount", "currency", "transaction_date"]
    list_filter = ["hotel", "type", "currency", "transaction_date"]
    list_select_related = ["hotel", "category", "method"]
    readonly_fields = ["created_at"]

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["hotel", "from_currency", "to_currency", "rate", "effective_date"]
    list_filter = ["hotel", "from_currency", "to_currency"]

@admin.register(DailyClosing)
class DailyClosingAdmin(admin.ModelAdmin):
    list_display = ["hotel", "business_date", "status", "total_income", "total_expense", "net"]
    list_filter = ["hotel", "status"]
    readonly_fields = ["total_income", "total_expense", "net", "opened_at", "closed_at"]

@admin.register(MonthlyClosing)
class MonthlyClosingAdmin(admin.ModelAdmin):
    list_display = ["hotel", "year", "month", "status", "total_income", "net"]
    list_filter = ["hotel", "status", "year"]
