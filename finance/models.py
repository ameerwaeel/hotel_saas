"""
finance/models.py
=================
المسار: finance/models.py
Phase: 6 — Payments + Finance + Multi-Currency + Closings

Models:
  ┌───────────────────────────────────────────────────────────────┐
  │  FinanceCategory      → تصنيفات الإيرادات والمصروفات         │
  │  FinancialTransaction → معاملات مالية (linked to payment)    │
  │  ExchangeRate         → أسعار صرف العملات (للتقارير فقط)    │
  │  DailyClosing         → إغلاق يومي مع لوك بعد الإغلاق       │
  │  MonthlyClosing       → إغلاق شهري                           │
  └───────────────────────────────────────────────────────────────┘

⚠️ Never FloatField for money — DecimalField everywhere.
⚠️ DailyClosing: select_for_update() لمنع double-closing race condition.
⚠️ بعد إغلاق اليوم: Service Layer يمنع mutations على transactions بتاريخه.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin, SoftDeleteModel
from common.models.managers import TenantManager


class TransactionType(models.TextChoices):
    INCOME = "income", _("Income")
    EXPENSE = "expense", _("Expense")
    REFUND = "refund", _("Refund")
    ADJUSTMENT = "adjustment", _("Adjustment")


class ClosingStatus(models.TextChoices):
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")


# ---------------------------------------------------------------------------
# FinanceCategory
# ---------------------------------------------------------------------------

class FinanceCategory(BaseModel, HotelOwnedMixin):
    """تصنيفات الإيرادات والمصروفات لكل فندق."""
    objects = TenantManager()

    name = models.CharField(max_length=100, verbose_name=_("Category Name"))
    type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name=_("Type"),
    )
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Finance Category")
        verbose_name_plural = _("Finance Categories")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "name", "type"],
                name="unique_finance_category_per_hotel",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.type}) @ {self.hotel.name}"


# ---------------------------------------------------------------------------
# FinancialTransaction
# ---------------------------------------------------------------------------

class FinancialTransaction(BaseModel, HotelOwnedMixin, SoftDeleteModel):
    """
    معاملة مالية.

    ⚠️ SoftDeleteModel — لا نحذف سجلات مالية نهائياً (audit trail).
    ⚠️ بعد DailyClosing.status=closed لتاريخ الـ transaction:
       Service Layer يرفض أي إضافة/تعديل (not the Serializer alone).

    Fields:
        type: income / expense / refund / adjustment
        category: الفئة
        amount: المبلغ (Decimal)
        currency: العملة
        method: طريقة الدفع
        transaction_date: التاريخ
        payment: FK للمدفوعة (اختياري)
        reservation: FK للحجز (اختياري)
        notes: ملاحظات
        created_by: من أنشأ المعاملة
    """
    objects = TenantManager()

    type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        db_index=True,
        verbose_name=_("Transaction Type"),
    )
    category = models.ForeignKey(
        FinanceCategory,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("Category"),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Amount"),
        help_text="Always DecimalField — never FloatField",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        db_index=True,
        verbose_name=_("Currency"),
    )
    method = models.ForeignKey(
        "payments.PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
        verbose_name=_("Payment Method"),
    )
    transaction_date = models.DateField(
        db_index=True,
        verbose_name=_("Transaction Date"),
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
        verbose_name=_("Related Payment"),
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
        verbose_name=_("Related Reservation"),
    )
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Financial Transaction")
        verbose_name_plural = _("Financial Transactions")
        indexes = [
            models.Index(fields=["hotel", "transaction_date"], name="idx_ftx_hotel_date"),
            models.Index(fields=["hotel", "currency", "transaction_date"], name="idx_ftx_hotel_currency_date"),
            models.Index(fields=["hotel", "type", "transaction_date"], name="idx_ftx_hotel_type_date"),
        ]

    def __str__(self):
        return f"{self.type} {self.amount} {self.currency} — {self.transaction_date}"


# ---------------------------------------------------------------------------
# ExchangeRate
# ---------------------------------------------------------------------------

class ExchangeRate(BaseModel, HotelOwnedMixin):
    """
    أسعار الصرف (للتقارير فقط — لا تُعدِّل السجلات الأصلية).

    ⚠️ لا نحوّل العملة تلقائياً في أي عملية مالية.
    ⚠️ التقارير تُجمِّع GROUP BY currency ثم تُعرض الأسعار المحوّلة
       للعرض فقط باستخدام ExchangeRate.

    Fields:
        from_currency, to_currency: زوج العملات
        rate: سعر الصرف (Decimal)
        effective_date: تاريخ سريان السعر
    """
    objects = TenantManager()

    from_currency = models.CharField(max_length=3, verbose_name=_("From Currency"))
    to_currency = models.CharField(max_length=3, verbose_name=_("To Currency"))
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        verbose_name=_("Exchange Rate"),
        help_text="DecimalField — high precision for currency conversion",
    )
    effective_date = models.DateField(db_index=True, verbose_name=_("Effective Date"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Exchange Rate")
        verbose_name_plural = _("Exchange Rates")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "from_currency", "to_currency", "effective_date"],
                name="unique_exchange_rate_per_hotel_date",
            )
        ]

    def __str__(self):
        return f"1 {self.from_currency} = {self.rate} {self.to_currency} ({self.effective_date})"


# ---------------------------------------------------------------------------
# DailyClosing
# ---------------------------------------------------------------------------

class DailyClosing(BaseModel, HotelOwnedMixin):
    """
    الإغلاق المالي اليومي.

    ⚠️ بعد status=CLOSED:
       - أي محاولة إضافة/تعديل transaction بتاريخ هذا اليوم يجب أن ترفضها
         Service Layer (لا الـ Serializer وحدها).
       - نستخدم select_for_update() عند الإغلاق لمنع double-closing race condition.

    ⚠️ Celery Beat task: تُغلَّق تلقائياً إذا لم تُغلَّق يدوياً.

    Fields:
        business_date: تاريخ اليوم التجاري
        status: open / closed
        total_income: مجموع الإيرادات (snapshot)
        total_expense: مجموع المصروفات (snapshot)
        net: صافي (snapshot)
        currency: العملة الرئيسية للملخص
        opened_at, closed_at: أوقات الفتح والإغلاق
        closed_by: من أغلق اليوم
        notes: ملاحظات
    """
    objects = TenantManager()

    business_date = models.DateField(
        db_index=True,
        verbose_name=_("Business Date"),
    )
    status = models.CharField(
        max_length=10,
        choices=ClosingStatus.choices,
        default=ClosingStatus.OPEN,
        db_index=True,
        verbose_name=_("Status"),
    )
    total_income = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name=_("Total Income (snapshot)"),
    )
    total_expense = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name=_("Total Expense (snapshot)"),
    )
    net = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name=_("Net (snapshot)"),
    )
    currency = models.CharField(max_length=3, default="USD", verbose_name=_("Summary Currency"))
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Opened At"))
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Closed At"))
    closed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="daily_closings",
    )
    notes = models.TextField(blank=True)

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Daily Closing")
        verbose_name_plural = _("Daily Closings")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "business_date"],
                name="unique_daily_closing_per_hotel_date",
            )
        ]

    def __str__(self):
        return f"Daily Closing {self.business_date} @ {self.hotel.name} [{self.status}]"


# ---------------------------------------------------------------------------
# MonthlyClosing
# ---------------------------------------------------------------------------

class MonthlyClosing(BaseModel, HotelOwnedMixin):
    """الإغلاق الشهري — يجمع الإغلاقات اليومية لشهر كامل."""
    objects = TenantManager()

    year = models.PositiveSmallIntegerField(db_index=True, verbose_name=_("Year"))
    month = models.PositiveSmallIntegerField(db_index=True, verbose_name=_("Month"))
    status = models.CharField(
        max_length=10,
        choices=ClosingStatus.choices,
        default=ClosingStatus.OPEN,
        verbose_name=_("Status"),
    )
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="monthly_closings",
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Monthly Closing")
        verbose_name_plural = _("Monthly Closings")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "year", "month"],
                name="unique_monthly_closing_per_hotel",
            )
        ]

    def __str__(self):
        return f"Monthly Closing {self.year}/{self.month:02d} @ {self.hotel.name} [{self.status}]"
