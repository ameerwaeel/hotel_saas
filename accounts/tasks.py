"""
accounts/tasks.py
=================
المسار: accounts/tasks.py
الوظيفة: مهام Celery الخلفية الخاصة بالحسابات (Authentication & Accounts).
         تتضمن:
           - إرسال رسائل البريد الإلكتروني بشكل غير متزامن (Async Emails)
           - إرسال روابط إعادة تعيين كلمة المرور
           - إرسال دعوات أعضاء الفنادق ورسائل الترحيب
"""

import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("hotel_saas")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_async_email(self, subject: str, message: str, recipient_list: list[str], html_message: str = None) -> bool:
    """
    مهمة Celery خلفية لإرسال رسائل البريد الإلكتروني بشكل غير متزامن (Asynchronous Email Delivery).
    
    الميزات:
      - لا تُعطّل دورة حياة طلب HTTP (Non-blocking).
      - تدعم إعادة المحاولة التلقائية (Retry) حتى 3 مرات عند حدوث مشاكل في الشبكة أو SMTP.
      - تسجيل تفصيلي للنجاح أو الفشل.
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "HOTEL SaaS <noreply@hotelsaas.com>")
    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(
            "Async email sent successfully",
            extra={
                "subject": subject,
                "recipients": recipient_list,
                "sent_count": sent_count,
            },
        )
        return True
    except Exception as exc:
        logger.error(
            f"Failed to send async email: {str(exc)}",
            extra={
                "subject": subject,
                "recipients": recipient_list,
                "error": str(exc),
            },
            exc_info=True,
        )
        # إعادة المحاولة في حالة الفشل
        raise self.retry(exc=exc)


def send_mail_resilient(subject: str, message: str, recipient_list: list[str], html_message: str = None) -> bool:
    """
    دالة مساعدة مرنة (Resilient Helper) لإرسال البريد الإلكتروني:
    1. تحاول إرسال المهمة عبر Celery الخلفي (.delay).
    2. في حال كان خادم Redis غير متصل محلياً (ConnectionError) أو في بيئة الاختبارات،
       تتراجع فوراً وبأمان للإرسال المتزامن (Direct Synchronous Send) لضمان عدم توقف النظام أبداً.
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "HOTEL SaaS <noreply@hotelsaas.com>")
    
    # إذا كانت بيئة الاختبار أو وضع Eager مفعلاً
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        try:
            send_async_email(subject, message, recipient_list, html_message=html_message)
            return True
        except Exception:
            return False

    try:
        # محاولة الإرسال غير المتزامن عبر Celery
        send_async_email.delay(subject, message, recipient_list, html_message=html_message)
        logger.info(f"Email task queued to Celery: '{subject}' to {recipient_list}")
        return True
    except Exception as e:
        # إذا كان Redis غير مشغل محلياً، أرسل فوراً عبر SMTP المباشر كـ Fallback
        logger.warning(
            f"Celery broker unavailable ({str(e)}). Falling back to direct synchronous email sending.",
            extra={"subject": subject, "recipients": recipient_list},
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email sent via synchronous fallback: '{subject}' to {recipient_list}")
            return True
        except Exception as sync_exc:
            logger.error(f"Synchronous email fallback also failed: {str(sync_exc)}", exc_info=True)
            return False
