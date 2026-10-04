"""
maintenance/tasks.py
====================
المسار: maintenance/tasks.py
Phase: 7 — Maintenance Celery Tasks
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(
    name="maintenance.tasks.notify_high_priority_issue",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # إعادة المحاولة بعد 60 ثانية
)
def notify_high_priority_issue(self, issue_id: str):
    """
    إرسال إشعار عند إنشاء RoomIssue بأولوية عالية.
    
    ⚠️ max_retries=3: يُعيد المحاولة 3 مرات عند الفشل.
    ⚠️ bind=True: للوصول إلى self.retry().
    
    في Phase 8: سيُرسل إشعار حقيقي (In-App + Email + SMS)
    عبر Notification model و NotificationChannel abstraction.
    """
    from maintenance.models import RoomIssue
    try:
        issue = (
            RoomIssue.objects
            .select_related("room__hotel", "assigned_to__user")
            .get(id=issue_id)
        )
    except RoomIssue.DoesNotExist:
        logger.warning(f"RoomIssue {issue_id} not found for notification.")
        return

    hotel = issue.room.hotel
    room_number = issue.room.room_number
    priority = issue.priority

    logger.warning(
        f"🔴 HIGH PRIORITY ISSUE [{priority.upper()}]: "
        f"Room {room_number} @ {hotel.name} — {issue.title}"
    )

    # Phase 8: هنا سيُرسل:
    # - In-app notification لكل managers في الفندق
    # - Email للمسؤول
    # - SMS/WhatsApp اختياري

    # MVP: log فقط
    logger.info(
        f"Notification sent for RoomIssue {issue_id} "
        f"(Phase 8 will implement real channels)"
    )
    return {"issue_id": issue_id, "notified": True}
