"""
housekeeping/models.py
======================
المسار: housekeeping/models.py
Phase: 7 — Housekeeping

Models:
  RoomCleaning → مهمة تنظيف غرفة بعد الـ checkout
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin
from common.models.managers import TenantManager


class CleaningStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    IN_PROGRESS = "in_progress", _("In Progress")
    COMPLETED = "completed", _("Completed")
    INSPECTED = "inspected", _("Inspected")


class RoomCleaning(BaseModel, HotelOwnedMixin):
    """
    مهمة تنظيف غرفة.

    ⚠️ تُنشَأ صراحةً من CheckoutService.checkout() — لا signals متشابكة.
    ⚠️ بعد الـ inspection، يمكن تغيير حالة الغرفة إلى AVAILABLE
       (بشرط عدم وجود blocking RoomIssue — يتحقق RoomService).

    Workflow: pending → in_progress → completed → inspected
    بعد inspected: RoomService.mark_available() يُغيّر Room.status إلى AVAILABLE

    Fields:
        room: الغرفة
        assigned_to: الموظف المسؤول عن التنظيف
        reservation: الحجز الذي سبب مهمة التنظيف (اختياري)
        status: حالة المهمة
        started_at, completed_at, inspected_at: أوقات المراحل
        notes: ملاحظات
    """

    objects = TenantManager()

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="cleanings",
        db_index=True,
        verbose_name=_("Room"),
    )
    assigned_to = models.ForeignKey(
        "customers.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleaning_tasks",
        verbose_name=_("Assigned To"),
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleaning_tasks",
        verbose_name=_("Related Reservation"),
    )
    status = models.CharField(
        max_length=20,
        choices=CleaningStatus.choices,
        default=CleaningStatus.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started At"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed At"))
    inspected_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Inspected At"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Room Cleaning")
        verbose_name_plural = _("Room Cleanings")
        indexes = [
            models.Index(fields=["hotel", "status"], name="idx_cleaning_hotel_status"),
            models.Index(fields=["room", "status"], name="idx_cleaning_room_status"),
        ]

    def __str__(self):
        return f"Cleaning Room {self.room.room_number} [{self.status}]"
