"""
payments/services.py
====================
المسار: payments/services.py
Phase: 6 — Payments
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from payments.models import Payment, PaymentMethod, PaymentStatus


class PaymentMethodService:
    @staticmethod
    def create(hotel, name: str, type: str = "cash", description: str = "") -> PaymentMethod:
        method = PaymentMethod(hotel=hotel, name=name, type=type, description=description)
        method.full_clean()
        method.save()
        return method


class PaymentService:
    """خدمات المدفوعات."""

    @staticmethod
    @transaction.atomic
    def create(
        hotel,
        method: PaymentMethod,
        amount: Decimal,
        currency: str,
        payment_date,
        reservation=None,
        reference: str = "",
        notes: str = "",
        processed_by=None,
    ) -> Payment:
        """
        إنشاء دفعة جديدة.

        ⚠️ بعد الإنشاء، يُنشئ FinancialTransaction تلقائياً عبر FinanceService.
        ⚠️ يتحقق من أن تاريخ الدفعة ليس في يوم مغلق (DailyClosing.status=closed).
        """
        from finance.services import FinanceService

        # التحقق من أن اليوم غير مغلق
        FinanceService.validate_date_not_closed(hotel, payment_date)

        if amount <= 0:
            raise ValidationError(_("Payment amount must be positive."))

        payment = Payment(
            hotel=hotel,
            reservation=reservation,
            amount=amount,
            currency=currency,
            method=method,
            payment_date=payment_date,
            reference=reference,
            status=PaymentStatus.COMPLETED,
            notes=notes,
            processed_by=processed_by,
        )
        payment.save()

        # إنشاء FinancialTransaction مرتبطة تلقائياً
        FinanceService.create_income_transaction(
            hotel=hotel,
            payment=payment,
            reservation=reservation,
            created_by=processed_by,
        )

        return payment

    @staticmethod
    def refund(payment: Payment, reason: str = "") -> Payment:
        """إرجاع دفعة."""
        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError(_("Can only refund completed payments."))
        payment.status = PaymentStatus.REFUNDED
        payment.notes = f"[REFUNDED] {reason}\n{payment.notes}"
        payment.save(update_fields=["status", "notes", "updated_at"])
        return payment
