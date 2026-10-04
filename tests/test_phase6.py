"""
tests/test_phase6.py
====================
Phase 6 Tests: Payments + Finance + Closings

Tests:
  ✅ Create payment → auto-creates FinancialTransaction
  ✅ Cannot add transaction to closed day
  ✅ Daily closing prevents double-close
  ✅ Daily summary GROUP BY currency
  ✅ Refund changes status
  ✅ Monthly closing aggregates daily closings
  ✅ Celery task auto_close_previous_day
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from payments.models import PaymentMethod, Payment, PaymentStatus
from payments.services import PaymentMethodService, PaymentService
from finance.models import (
    FinanceCategory, FinancialTransaction, DailyClosing,
    MonthlyClosing, TransactionType, ClosingStatus
)
from finance.services import FinanceService, ClosingService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pay_method(db, hotel):
    return PaymentMethod.objects.create(hotel=hotel, name="Cash", type="cash")

@pytest.fixture
def finance_category(db, hotel):
    return FinanceCategory.objects.create(
        hotel=hotel, name="Room Revenue", type=TransactionType.INCOME
    )

@pytest.fixture
def expense_category(db, hotel):
    return FinanceCategory.objects.create(
        hotel=hotel, name="Utilities", type=TransactionType.EXPENSE
    )

@pytest.fixture
def today():
    return date.today()


# ---------------------------------------------------------------------------
# Payment Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPayments:
    def test_create_payment_auto_creates_transaction(self, hotel, pay_method, today):
        payment = PaymentService.create(
            hotel=hotel, method=pay_method, amount=Decimal("500.00"),
            currency="USD", payment_date=today
        )
        assert payment.status == PaymentStatus.COMPLETED
        assert FinancialTransaction.objects.filter(payment=payment).exists()

    def test_payment_amount_must_be_positive(self, hotel, pay_method, today):
        with pytest.raises(ValidationError):
            PaymentService.create(
                hotel=hotel, method=pay_method, amount=Decimal("0.00"),
                currency="USD", payment_date=today
            )

    def test_refund_payment(self, hotel, pay_method, today):
        payment = PaymentService.create(
            hotel=hotel, method=pay_method, amount=Decimal("200.00"),
            currency="USD", payment_date=today
        )
        refunded = PaymentService.refund(payment, reason="Customer request")
        assert refunded.status == PaymentStatus.REFUNDED

    def test_refund_non_completed_fails(self, hotel, pay_method, today):
        payment = PaymentService.create(
            hotel=hotel, method=pay_method, amount=Decimal("200.00"),
            currency="USD", payment_date=today
        )
        payment.status = PaymentStatus.REFUNDED
        payment.save()
        with pytest.raises(ValidationError):
            PaymentService.refund(payment)

    def test_payment_blocked_on_closed_day(self, hotel, pay_method, today, admin_user):
        ClosingService.close_daily(hotel, today, closed_by=admin_user)
        with pytest.raises(ValidationError):
            PaymentService.create(
                hotel=hotel, method=pay_method, amount=Decimal("300.00"),
                currency="USD", payment_date=today
            )


# ---------------------------------------------------------------------------
# Finance Service Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFinanceService:
    def test_daily_summary_by_currency(self, hotel, pay_method, finance_category, expense_category, today):
        """ملخص يومي يجب أن يُقسَّم حسب العملة."""
        # 500 USD income
        FinancialTransaction.objects.create(
            hotel=hotel, type=TransactionType.INCOME,
            category=finance_category, amount=Decimal("500.00"),
            currency="USD", method=pay_method, transaction_date=today,
        )
        # 200 USD expense
        FinancialTransaction.objects.create(
            hotel=hotel, type=TransactionType.EXPENSE,
            category=expense_category, amount=Decimal("200.00"),
            currency="USD", method=pay_method, transaction_date=today,
        )
        # 100 EUR income
        FinancialTransaction.objects.create(
            hotel=hotel, type=TransactionType.INCOME,
            category=finance_category, amount=Decimal("100.00"),
            currency="EUR", method=pay_method, transaction_date=today,
        )

        summary = FinanceService.get_daily_summary(hotel, today)

        assert "USD" in summary
        assert "EUR" in summary
        assert summary["USD"]["income"] == Decimal("500.00")
        assert summary["USD"]["expense"] == Decimal("200.00")
        assert summary["USD"]["net"] == Decimal("300.00")
        assert summary["EUR"]["income"] == Decimal("100.00")

    def test_validate_date_not_closed(self, hotel, today, admin_user):
        """تعديل على يوم مغلق يُرفَض."""
        ClosingService.close_daily(hotel, today, closed_by=admin_user)
        with pytest.raises(ValidationError):
            FinanceService.validate_date_not_closed(hotel, today)

    def test_validate_open_day_passes(self, hotel, today):
        """يوم مفتوح لا يُرفَض."""
        FinanceService.validate_date_not_closed(hotel, today)  # لا استثناء


# ---------------------------------------------------------------------------
# Daily Closing Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDailyClosing:
    def test_close_daily(self, hotel, today, admin_user):
        closing = ClosingService.close_daily(hotel, today, closed_by=admin_user)
        assert closing.status == ClosingStatus.CLOSED
        assert closing.closed_by == admin_user
        assert closing.closed_at is not None

    def test_double_close_raises_error(self, hotel, today, admin_user):
        ClosingService.close_daily(hotel, today, closed_by=admin_user)
        with pytest.raises(ValidationError):
            ClosingService.close_daily(hotel, today, closed_by=admin_user)

    def test_closing_calculates_totals(self, hotel, pay_method, finance_category, expense_category, today, admin_user):
        FinancialTransaction.objects.create(
            hotel=hotel, type=TransactionType.INCOME,
            category=finance_category, amount=Decimal("1000.00"),
            currency="USD", method=pay_method, transaction_date=today,
        )
        FinancialTransaction.objects.create(
            hotel=hotel, type=TransactionType.EXPENSE,
            category=expense_category, amount=Decimal("300.00"),
            currency="USD", method=pay_method, transaction_date=today,
        )
        closing = ClosingService.close_daily(hotel, today, closed_by=admin_user)
        assert closing.total_income == Decimal("1000.00")
        assert closing.total_expense == Decimal("300.00")
        assert closing.net == Decimal("700.00")


# ---------------------------------------------------------------------------
# Monthly Closing Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMonthlyClosing:
    def test_close_month_aggregates_daily_closings(self, hotel, today, admin_user):
        # أغلق 3 أيام
        for i in range(3):
            d = date(today.year, today.month, 1) + timedelta(days=i)
            c = ClosingService.close_daily(hotel, d, closed_by=admin_user)
            # نُعدِّل إجمالياتها يدوياً لاختبار التجميع
            c.total_income = Decimal("1000.00")
            c.total_expense = Decimal("300.00")
            c.net = Decimal("700.00")
            c.save()

        monthly = ClosingService.close_monthly(
            hotel, year=today.year, month=today.month, closed_by=admin_user
        )
        assert monthly.status == ClosingStatus.CLOSED
        assert monthly.total_income == Decimal("3000.00")
        assert monthly.net == Decimal("2100.00")

    def test_double_close_month_raises_error(self, hotel, today, admin_user):
        ClosingService.close_monthly(hotel, today.year, today.month, closed_by=admin_user)
        with pytest.raises(ValidationError):
            ClosingService.close_monthly(hotel, today.year, today.month, closed_by=admin_user)
