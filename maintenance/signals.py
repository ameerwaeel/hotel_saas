"""
maintenance/signals.py
======================
المسار: maintenance/signals.py
Phase: 7 — Maintenance Notifications

⚠️ Signal يُطلق Celery task عند إنشاء RoomIssue بأولوية عالية.
   مُفصول عن الـ request/response cycle بالكامل.

   Pattern:
     Signal (post_save on RoomIssue) → Celery Task (notify_high_priority_issue)
     
   لماذا Celery وليس signal مباشر؟
     - لا نريد أن يفشل الـ request بسبب فشل الإشعار
     - Celery يُعيد المحاولة تلقائياً عند الفشل
     - مُفصول تماماً (decoupled)
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender="maintenance.RoomIssue")
def on_room_issue_created(sender, instance, created, **kwargs):
    """
    عند إنشاء RoomIssue بأولوية HIGH أو CRITICAL:
    → يُطلق Celery task لإرسال إشعار فوري لمدير الصيانة.
    
    ⚠️ نتحقق من created=True فقط (لا نُرسل عند كل تعديل).
    ⚠️ استخدام .delay() بدل استدعاء مباشر → decoupled من الـ request.
    """
    if not created:
        return

    if instance.is_high_priority:
        try:
            from maintenance.tasks import notify_high_priority_issue
            notify_high_priority_issue.delay(str(instance.id))
            logger.info(
                f"Enqueued high-priority notification for RoomIssue {instance.id}"
            )
        except Exception as e:
            # لا نُفشل الـ request إذا فشل Celery
            logger.error(
                f"Failed to enqueue notification for RoomIssue {instance.id}: {e}"
            )
