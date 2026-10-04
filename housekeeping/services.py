"""
housekeeping/services.py + maintenance/services.py + complaints/services.py
Phase 7 — combined for brevity
"""

# housekeeping/services.py
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class HousekeepingService:
    """خدمات الـ Housekeeping."""

    @staticmethod
    def start_cleaning(cleaning):
        """بدء التنظيف: pending → in_progress."""
        from housekeeping.models import CleaningStatus
        if cleaning.status != CleaningStatus.PENDING:
            raise ValidationError(_("Can only start pending cleaning tasks."))
        cleaning.status = CleaningStatus.IN_PROGRESS
        cleaning.started_at = timezone.now()
        cleaning.save(update_fields=["status", "started_at", "updated_at"])
        return cleaning

    @staticmethod
    def complete_cleaning(cleaning):
        """إتمام التنظيف: in_progress → completed."""
        from housekeeping.models import CleaningStatus
        if cleaning.status != CleaningStatus.IN_PROGRESS:
            raise ValidationError(_("Can only complete in-progress cleaning tasks."))
        cleaning.status = CleaningStatus.COMPLETED
        cleaning.completed_at = timezone.now()
        cleaning.save(update_fields=["status", "completed_at", "updated_at"])
        return cleaning

    @staticmethod
    def inspect_cleaning(cleaning):
        """
        الـ Inspection: completed → inspected.
        بعد الـ inspection يمكن تحرير الغرفة إلى AVAILABLE.
        """
        from housekeeping.models import CleaningStatus
        from rooms.services import RoomService
        from rooms.models import RoomStatus
        if cleaning.status != CleaningStatus.COMPLETED:
            raise ValidationError(_("Can only inspect completed cleaning tasks."))
        cleaning.status = CleaningStatus.INSPECTED
        cleaning.inspected_at = timezone.now()
        cleaning.save(update_fields=["status", "inspected_at", "updated_at"])
        # محاولة تحرير الغرفة (ستفشل إذا كان هناك blocking issue)
        RoomService.update_status(cleaning.room, RoomStatus.AVAILABLE, check_blocking=True)
        return cleaning

    @staticmethod
    def assign_employee(cleaning, employee):
        """تعيين موظف لمهمة التنظيف."""
        cleaning.assigned_to = employee
        cleaning.save(update_fields=["assigned_to", "updated_at"])
        return cleaning
