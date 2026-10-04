"""maintenance/services.py — Phase 7"""
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class MaintenanceService:
    @staticmethod
    def create_issue(hotel, room, title, description="", priority="medium",
                     blocking=False, assigned_to=None, created_by=None):
        from maintenance.models import RoomIssue
        issue = RoomIssue(
            hotel=hotel, room=room, title=title, description=description,
            priority=priority, blocking=blocking, assigned_to=assigned_to,
        )
        issue.full_clean()
        issue.save()
        # Signal سيُطلق Celery task تلقائياً إذا كانت الأولوية عالية
        return issue

    @staticmethod
    def resolve_issue(issue, notes=""):
        from maintenance.models import IssueStatus
        issue.status = IssueStatus.RESOLVED
        issue.resolved_at = timezone.now()
        if notes:
            issue.notes = f"{notes}\n{issue.notes}"
        issue.save(update_fields=["status", "resolved_at", "notes", "updated_at"])
        return issue

    @staticmethod
    def assign_issue(issue, employee):
        from maintenance.models import IssueStatus
        issue.assigned_to = employee
        if issue.status == IssueStatus.OPEN:
            issue.status = IssueStatus.IN_PROGRESS
        issue.save(update_fields=["assigned_to", "status", "updated_at"])
        return issue
