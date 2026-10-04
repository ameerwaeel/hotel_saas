"""
maintenance/models.py
=====================
المسار: maintenance/models.py
Phase: 7 — Maintenance

Models:
  RoomIssue → مشكلة/عطل في غرفة، قد تكون blocking للـ availability
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin
from common.models.managers import TenantManager


class IssuePriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class IssueStatus(models.TextChoices):
    OPEN = "open", _("Open")
    IN_PROGRESS = "in_progress", _("In Progress")
    RESOLVED = "resolved", _("Resolved")
    CLOSED = "closed", _("Closed")


class RoomIssue(BaseModel, HotelOwnedMixin):
    """
    مشكلة/عطل في غرفة.

    ⚠️ blocking=True يمنع Room.status = AVAILABLE:
       RoomService.mark_available() يتحقق من وجود blocking issues
       قبل السماح بتغيير الحالة.

    ⚠️ Index على (status, priority) — query الأكثر شيوعاً:
       "كل المشاكل المفتوحة عالية الأولوية".

    ⚠️ Notifications: إذا priority=HIGH أو CRITICAL، يُطلَق Celery task
       من maintenance/signals.py لإرسال إشعار فوري.

    ⚠️ N+1 في Room list مع has_blocking_issue:
       استخدم annotate(Exists(...)) في Selector بدل SerializerMethodField.

    Fields:
        room: الغرفة
        title: عنوان المشكلة
        description: وصف تفصيلي
        status: open/in_progress/resolved/closed
        priority: low/medium/high/critical
        blocking: هل تمنع الغرفة من أن تكون AVAILABLE؟
        assigned_to: الموظف المسؤول
        resolved_at: وقت الحل
        notes: ملاحظات
    """

    objects = TenantManager()

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="issues",
        db_index=True,
        verbose_name=_("Room"),
    )
    title = models.CharField(max_length=200, verbose_name=_("Issue Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    status = models.CharField(
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.OPEN,
        db_index=True,
        verbose_name=_("Status"),
    )
    priority = models.CharField(
        max_length=10,
        choices=IssuePriority.choices,
        default=IssuePriority.MEDIUM,
        db_index=True,   # ← indexed for "open high-priority issues" query
        verbose_name=_("Priority"),
    )
    blocking = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Blocking"),
        help_text="If True, room cannot become AVAILABLE until this issue is resolved.",
    )
    assigned_to = models.ForeignKey(
        "customers.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues",
        verbose_name=_("Assigned To"),
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Resolved At"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Room Issue")
        verbose_name_plural = _("Room Issues")
        indexes = [
            # ← أهم composite index: "المشاكل المفتوحة عالية الأولوية"
            models.Index(fields=["hotel", "status", "priority"], name="idx_issue_hotel_status_prio"),
            models.Index(fields=["room", "status", "blocking"], name="idx_issue_room_blocking"),
        ]

    def __str__(self):
        return f"Issue: {self.title} in Room {self.room.room_number} [{self.priority}]"

    @property
    def is_high_priority(self) -> bool:
        return self.priority in [IssuePriority.HIGH, IssuePriority.CRITICAL]
