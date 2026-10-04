"""
payments/models.py
==================
المسار: payments/models.py
Phase: 6 — Payments + Finance + Multi-Currency + Closings

Models:
  ┌─────────────────────────────────────────────────────────────┐
  │  PaymentMethod  → طرق الدفع (كاش، بطاقة، حوالة، ...)        │
  │  Payment        → مدفوعات مرتبطة بالحجوزات                  │
  └─────────────────────────────────────────────────────────────┘

⚠️ Golden Rule: DecimalField أبداً لا FloatField للأموال.
⚠️ N+1 في payment list → select_related("reservation__customer", "method").
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin, SoftDeleteModel
from common.models.managers import TenantManager


class PaymentMethodType(models.TextChoices):
    CASH = "cash", _("Cash")
    CREDIT_CARD = "credit_card", _("Credit Card")
    DEBIT_CARD = "debit_card", _("Debit Card")
    BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
    ONLINE = "online", _("Online Payment")
    CHEQUE = "cheque", _("Cheque")
    OTHER = "other", _("Other")


class PaymentMethod(BaseModel, HotelOwnedMixin):
    """
    طريقة الدفع (مخصصة لكل فندق).

    Fields:
        name: اسم طريقة الدفع (e.g., "Visa", "Cash Register 1")
        type: نوع طريقة الدفع
        is_active: نشطة؟
    """
    objects = TenantManager()

    name = models.CharField(max_length=100, verbose_name=_("Name"))
    type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices,
        default=PaymentMethodType.CASH,
        verbose_name=_("Type"),
    )
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "name"],
                name="unique_payment_method_per_hotel",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.type}) @ {self.hotel.name}"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    REFUNDED = "refunded", _("Refunded")
    PARTIAL_REFUND = "partial_refund", _("Partial Refund")


class Payment(BaseModel, HotelOwnedMixin, SoftDeleteModel):
    """
    دفعة مرتبطة بحجز.

    ⚠️ SoftDeleteModel — لا نحذف سجلات مالية نهائياً.
    ⚠️ DecimalField للمبالغ — أبداً لا FloatField.
    ⚠️ currency مع amount — لا تحويل تلقائي (تُجمَّع GROUP BY currency في التقارير).

    Fields:
        reservation: FK للحجز (nullable — قد تكون مدفوعة مقدماً)
        amount: المبلغ (DecimalField)
        currency: العملة (ISO 4217)
        method: طريقة الدفع
        payment_date: تاريخ الدفع
        reference: رقم مرجعي (رقم إيصال/معاملة)
        status: حالة المدفوعة
        notes: ملاحظات
        processed_by: من استلم الدفعة
    """
    objects = TenantManager()

    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        db_index=True,
        verbose_name=_("Reservation"),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Amount"),
        help_text="Payment amount — DecimalField (never FloatField)",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        db_index=True,
        verbose_name=_("Currency"),
    )
    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("Payment Method"),
    )
    payment_date = models.DateField(
        db_index=True,
        verbose_name=_("Payment Date"),
    )
    reference = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Reference Number"),
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.COMPLETED,
        db_index=True,
        verbose_name=_("Status"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    processed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_payments",
        verbose_name=_("Processed By"),
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        indexes = [
            models.Index(fields=["hotel", "payment_date"], name="idx_payment_hotel_date"),
            models.Index(fields=["hotel", "currency", "payment_date"], name="idx_payment_curr_date"),
        ]

    def __str__(self):
        return f"Payment {self.amount} {self.currency} — {self.payment_date}"
