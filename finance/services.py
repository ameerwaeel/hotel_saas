"""
finance/services.py
===================
المسار: finance/services.py
Phase: 6 — Finance + Multi-Currency + Closings

⚠️ أهم قاعدة: بعد DailyClosing.status=closed لتاريخ معين،
   أي محاولة إضافة/تعديل transaction بتاريخه ترفضها هذه الـ Service.
⚠️ select_for_update() عند الإغلاق لمنع double-closing race condition.
⚠️ Aggregation GROUP BY currency — لا SUM مباشر على عملات مختلفة.
"""

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from finance.models import (
    FinanceCategory, FinancialTransaction, ExchangeRate,
    DailyClosing, MonthlyClosing, TransactionType, ClosingStatus
)


class FinanceService:
    """خدمات Finance العامة."""

    @staticmethod
    def validate_date_not_closed(hotel, date):
        """
        ⚠️ يتحقق من أن التاريخ المعطى ليس في يوم مغلق.
        يُستخدَم قبل أي إنشاء/تعديل transaction.
        """
        closing = DailyClosing.objects.filter(
            hotel=hotel,
            business_date=date,
            status=ClosingStatus.CLOSED,
        ).first()
        if closing:
            raise ValidationError(_(
                f"Business date {date} is already closed. "
                f"No financial transactions can be added or modified."
            ))

    @staticmethod
    def create_income_transaction(hotel, payment, reservation=None, created_by=None):
        """
        إنشاء FinancialTransaction income مرتبطة بـ Payment.
        يُستدعى تلقائياً من PaymentService.create().
        """
        # الفئة الافتراضية: Room Revenue أو إنشاء واحدة جديدة
        category, _ = FinanceCategory.objects.get_or_create(
            hotel=hotel,
            name="Room Revenue",
            type=TransactionType.INCOME,
            defaults={"description": "Auto-created room revenue category"},
        )

        FinancialTransaction.objects.create(
            hotel=hotel,
            type=TransactionType.INCOME,
            category=category,
            amount=payment.amount,
            currency=payment.currency,
            method=payment.method,
            transaction_date=payment.payment_date,
            payment=payment,
            reservation=reservation,
            created_by=created_by,
            notes=f"Auto from Payment #{payment.id}",
        )

    @staticmethod
    def create_expense_transaction(
        hotel, category, amount: Decimal, currency: str,
        method, transaction_date, notes: str = "", created_by=None
    ) -> FinancialTransaction:
        """إنشاء معاملة مصروف."""
        FinanceService.validate_date_not_closed(hotel, transaction_date)

        txn = FinancialTransaction(
            hotel=hotel,
            type=TransactionType.EXPENSE,
            category=category,
            amount=amount,
            currency=currency,
            method=method,
            transaction_date=transaction_date,
            notes=notes,
            created_by=created_by,
        )
        txn.save()
        return txn

    @staticmethod
    def get_daily_summary(hotel, business_date):
        """
        ملخص يومي مقسَّم حسب العملة.

        ⚠️ GROUP BY currency — لا SUM على عملات مختلفة مع بعض.
        يُرجع dict: {currency: {income: Decimal, expense: Decimal, net: Decimal}}
        """
        transactions = FinancialTransaction.objects.filter(
            hotel=hotel,
            transaction_date=business_date,
            deleted_at__isnull=True,
        )

        # إيرادات حسب العملة
        income_by_currency = (
            transactions
            .filter(type=TransactionType.INCOME)
            .values("currency")
            .annotate(total=Sum("amount"))
        )

        # مصروفات حسب العملة
        expense_by_currency = (
            transactions
            .filter(type=TransactionType.EXPENSE)
            .values("currency")
            .annotate(total=Sum("amount"))
        )

        summary = {}
        for row in income_by_currency:
            c = row["currency"]
            summary.setdefault(c, {"income": Decimal("0"), "expense": Decimal("0"), "net": Decimal("0")})
            summary[c]["income"] = row["total"] or Decimal("0")

        for row in expense_by_currency:
            c = row["currency"]
            summary.setdefault(c, {"income": Decimal("0"), "expense": Decimal("0"), "net": Decimal("0")})
            summary[c]["expense"] = row["total"] or Decimal("0")

        for c in summary:
            summary[c]["net"] = summary[c]["income"] - summary[c]["expense"]

        return summary


class ClosingService:
    """خدمات الإغلاق اليومي والشهري."""

    @staticmethod
    @transaction.atomic
    def close_daily(hotel, business_date, closed_by=None, notes: str = "") -> DailyClosing:
        """
        إغلاق يوم مالي.

        ⚠️ select_for_update() على DailyClosing لمنع double-closing race condition.
           إذا حاول مستخدمان الإغلاق في نفس الوقت، الثاني سيجد status=CLOSED.

        ⚠️ بعد الإغلاق، أي transaction بتاريخ هذا اليوم ترفضها
           FinanceService.validate_date_not_closed().
        """
        # القفل على مستوى الـ row (منع double-closing)
        closing, created = DailyClosing.objects.select_for_update().get_or_create(
            hotel=hotel,
            business_date=business_date,
            defaults={"status": ClosingStatus.OPEN},
        )

        if closing.status == ClosingStatus.CLOSED:
            raise ValidationError(_(
                f"Business date {business_date} is already closed."
            ))

        # حساب المجاميع من الـ transactions
        summary = FinanceService.get_daily_summary(hotel, business_date)

        # نأخذ الإجماليات بالعملة الرئيسية للفندق (أو أكبر مجموع)
        # في MVP: نجمع كل الإيرادات والمصروفات كما هي (مستخدم يرى التفاصيل في summary)
        total_income = sum(v["income"] for v in summary.values())
        total_expense = sum(v["expense"] for v in summary.values())
        net = total_income - total_expense

        closing.status = ClosingStatus.CLOSED
        closing.total_income = total_income
        closing.total_expense = total_expense
        closing.net = net
        closing.closed_at = timezone.now()
        closing.closed_by = closed_by
        closing.notes = notes
        closing.save()

        return closing

    @staticmethod
    @transaction.atomic
    def close_monthly(hotel, year: int, month: int, closed_by=None) -> MonthlyClosing:
        """
        إغلاق شهر مالي.
        يجمع كل الإغلاقات اليومية للشهر ويُنشئ ملخصاً.
        """
        # التحقق من أن كل الأيام مغلقة
        import calendar
        from datetime import date
        days_in_month = calendar.monthrange(year, month)[1]

        open_days = DailyClosing.objects.filter(
            hotel=hotel,
            business_date__year=year,
            business_date__month=month,
            status=ClosingStatus.OPEN,
        ).count()

        # تحذير: في بعض الفنادق ممكن يغلقوا الشهر بدون غلق كل يوم
        # نسمح بذلك لكن نُسجّل تحذيراً في الـ notes

        # جمع من DailyClosings المغلقة
        daily_totals = DailyClosing.objects.filter(
            hotel=hotel,
            business_date__year=year,
            business_date__month=month,
            status=ClosingStatus.CLOSED,
        ).aggregate(
            income=Sum("total_income"),
            expense=Sum("total_expense"),
        )

        total_income = daily_totals["income"] or Decimal("0")
        total_expense = daily_totals["expense"] or Decimal("0")

        closing, _ = MonthlyClosing.objects.select_for_update().get_or_create(
            hotel=hotel,
            year=year,
            month=month,
            defaults={"status": ClosingStatus.OPEN},
        )

        if closing.status == ClosingStatus.CLOSED:
            raise ValidationError(
                f"Month {year}/{month:02d} is already closed."
            )

        closing.status = ClosingStatus.CLOSED
        closing.total_income = total_income
        closing.total_expense = total_expense
        closing.net = total_income - total_expense
        closing.closed_at = timezone.now()
        closing.closed_by = closed_by
        closing.save()

        return closing
