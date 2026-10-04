"""
finance/tasks.py
================
المسار: finance/tasks.py
Phase: 6 — Celery Beat Auto-Close Task

⚠️ Celery Beat Task: تُشغَّل تلقائياً آخر اليوم (أو أول يوم التالي)
   لإغلاق اليوم المالي السابق إذا لم يُغلَّق يدوياً.
"""

from celery import shared_task
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name="finance.tasks.auto_close_previous_day")
def auto_close_previous_day():
    """
    Celery Beat Task — يُشغَّل يومياً في بداية اليوم الجديد.
    يُغلق اليوم السابق لكل فندق إذا لم يُغلَّق يدوياً.

    جدولة Celery Beat (في settings):
        CELERY_BEAT_SCHEDULE = {
            "auto-close-daily": {
                "task": "finance.tasks.auto_close_previous_day",
                "schedule": crontab(hour=1, minute=0),  # كل يوم الساعة 01:00
            }
        }
    """
    from finance.models import DailyClosing, ClosingStatus
    from finance.services import ClosingService
    from tenants.models import Hotel

    yesterday = date.today() - timedelta(days=1)

    hotels = Hotel.objects.filter(is_active=True)
    closed_count = 0
    error_count = 0

    for hotel in hotels:
        # تحقق إذا اليوم السابق مغلق بالفعل
        already_closed = DailyClosing.objects.filter(
            hotel=hotel,
            business_date=yesterday,
            status=ClosingStatus.CLOSED,
        ).exists()

        if not already_closed:
            try:
                ClosingService.close_daily(
                    hotel=hotel,
                    business_date=yesterday,
                    notes=f"Auto-closed by Celery Beat task on {date.today()}",
                )
                closed_count += 1
                logger.info(f"Auto-closed {yesterday} for hotel: {hotel.name}")
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to auto-close {yesterday} for hotel {hotel.name}: {e}"
                )

    logger.info(
        f"auto_close_previous_day completed: "
        f"{closed_count} closed, {error_count} errors."
    )
    return {"closed": closed_count, "errors": error_count}


@shared_task(name="finance.tasks.export_financial_report")
def export_financial_report(hotel_id: str, year: int, month: int, report_type: str = "pdf"):
    """
    Celery Task — تصدير تقرير مالي (PDF/Excel) بشكل غير متزامن.

    ⚠️ التصدير بطيء — لا يُشغَّل synchronously في الـ request.
       الـ View يُعيد {"task_id": "..."} والـ Frontend يستعلم عن النتيجة.

    Args:
        hotel_id: UUID الفندق
        year, month: الشهر والسنة
        report_type: "pdf" أو "excel"
    """
    from tenants.models import Hotel
    from finance.models import FinancialTransaction
    import uuid

    logger.info(f"Generating {report_type} report for hotel {hotel_id}, {year}/{month:02d}")

    try:
        hotel = Hotel.objects.get(id=hotel_id)

        transactions = FinancialTransaction.objects.filter(
            hotel=hotel,
            transaction_date__year=year,
            transaction_date__month=month,
            deleted_at__isnull=True,
        ).select_related("category", "method", "reservation").order_by("transaction_date")

        # في الـ MVP: نُعيد بيانات JSON فقط (PDF/Excel يحتاج WeasyPrint/openpyxl في Phase 8)
        report_data = {
            "hotel": hotel.name,
            "period": f"{year}/{month:02d}",
            "transaction_count": transactions.count(),
            "report_type": report_type,
            "status": "completed",
            "note": "Full PDF/Excel export will be implemented in Phase 8 with WeasyPrint/openpyxl",
        }

        logger.info(f"Report generated successfully for {hotel.name}")
        return report_data

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise
