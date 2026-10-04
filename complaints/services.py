"""complaints/services.py — Phase 7"""
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ComplaintService:
    @staticmethod
    def create(hotel, customer, title, description, category="", priority="medium",
               reservation=None, assigned_to=None):
        from complaints.models import CustomerComplaint
        complaint = CustomerComplaint(
            hotel=hotel, customer=customer, title=title, description=description,
            category=category, priority=priority, reservation=reservation,
            assigned_to=assigned_to,
        )
        complaint.full_clean()
        complaint.save()
        return complaint

    @staticmethod
    def resolve(complaint, resolution_notes=""):
        from complaints.models import ComplaintStatus
        complaint.status = ComplaintStatus.RESOLVED
        complaint.resolved_at = timezone.now()
        complaint.resolution_notes = resolution_notes
        complaint.save(update_fields=["status", "resolved_at", "resolution_notes", "updated_at"])
        return complaint

    @staticmethod
    def assign(complaint, employee):
        from complaints.models import ComplaintStatus
        complaint.assigned_to = employee
        if complaint.status == ComplaintStatus.OPEN:
            complaint.status = ComplaintStatus.IN_PROGRESS
        complaint.save(update_fields=["assigned_to", "status", "updated_at"])
        return complaint
