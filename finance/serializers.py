"""
finance/serializers.py
======================
"""
from rest_framework import serializers
from finance.models import (
    FinanceCategory, FinancialTransaction, ExchangeRate,
    DailyClosing, MonthlyClosing
)


class FinanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceCategory
        fields = ["id", "name", "type", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class FinancialTransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    method_name = serializers.SerializerMethodField()

    class Meta:
        model = FinancialTransaction
        fields = [
            "id", "type", "category", "category_name",
            "amount", "currency", "method", "method_name",
            "transaction_date", "reference", "notes",
            "payment", "reservation", "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "category_name", "method_name", "created_at"]

    def get_method_name(self, obj) -> str:
        return obj.method.name if obj.method else ""


class FinancialTransactionCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["income", "expense", "refund", "adjustment"])
    category = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=3, default="USD")
    method = serializers.UUIDField(required=False, allow_null=True)
    transaction_date = serializers.DateField()
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = [
            "id", "from_currency", "to_currency", "rate",
            "effective_date", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class DailyClosingSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.CharField(source="closed_by.full_name", read_only=True, default=None)

    class Meta:
        model = DailyClosing
        fields = [
            "id", "business_date", "status",
            "total_income", "total_expense", "net", "currency",
            "opened_at", "closed_at", "closed_by", "closed_by_name", "notes"
        ]
        read_only_fields = [
            "id", "total_income", "total_expense", "net",
            "opened_at", "closed_at", "closed_by_name"
        ]


class DailyClosingCloseSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class MonthlyClosingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyClosing
        fields = [
            "id", "year", "month", "status",
            "total_income", "total_expense", "net", "currency",
            "closed_at", "closed_by"
        ]
        read_only_fields = ["id", "total_income", "total_expense", "net", "closed_at"]


class DailySummarySerializer(serializers.Serializer):
    """Response for GET /finance/daily-summary/?date=..."""
    date = serializers.DateField()
    summary_by_currency = serializers.DictField()
    closing_status = serializers.CharField()
