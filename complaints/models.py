"""
complaints/models.py
====================
المسار: complaints/models.py
Phase: 7 — Complaints
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin
from common.models.managers import TenantManager


class ComplaintStatus(models.TextChoices):
    OPEN = "open", _("Open")
    IN_PROGRESS = "in_progress", _("In Progress")
    RESOLVED = "resolved", _("Resolved")
    CLOSED = "closed", _("Closed")


class ComplaintPriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class CustomerComplaint(BaseModel, HotelOwnedMixin):
    """
    شكوى عميل.

    Fields:
        customer: العميل
        reservation: الحجز المرتبط (اختياري)
        category: تصنيف الشكوى
        title: عنوان الشكوى
        description: التفاصيل
        status, priority: الحالة والأولوية
        assigned_to: الموظف المسؤول
        resolved_at: وقت الحل
        resolution_notes: ملاحظات الحل
    """

    objects = TenantManager()

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="complaints",
        db_index=True,
        verbose_name=_("Customer"),
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        verbose_name=_("Related Reservation"),
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name=_("Category"),
        help_text="e.g., Room Quality, Service, Noise, Billing",
    )
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    status = models.CharField(
        max_length=20,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.OPEN,
        db_index=True,
        verbose_name=_("Status"),
    )
    priority = models.CharField(
        max_length=10,
        choices=ComplaintPriority.choices,
        default=ComplaintPriority.MEDIUM,
        db_index=True,
        verbose_name=_("Priority"),
    )
    assigned_to = models.ForeignKey(
        "customers.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
        verbose_name=_("Assigned To"),
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Resolved At"))
    resolution_notes = models.TextField(blank=True, verbose_name=_("Resolution Notes"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Customer Complaint")
        verbose_name_plural = _("Customer Complaints")
        indexes = [
            models.Index(fields=["hotel", "status", "priority"], name="idx_complaint_hotel_status"),
            models.Index(fields=["hotel", "customer"], name="idx_complaint_hotel_customer"),
        ]

    def __str__(self):
        return f"Complaint: {self.title} by {self.customer.full_name} [{self.status}]"
