"""
common/middleware/request_id.py
================================
المسار: common/middleware/request_id.py
الوظيفة: Middleware يُولِّد UUID فريد لكل HTTP request ويُضيفه للـ response headers.

الاستخدام:
  - كل request يحصل على X-Request-ID header
  - request.request_id متاح في كل مكان (views, serializers, logging)
  - يُساعد في تتبع الأخطاء في الـ logs عن طريق request_id

مثال:
  Request:  GET /api/v1/rooms/
  Response: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000

  في الـ logs:
    {"request_id": "550e8400...", "level": "ERROR", "message": "..."

مُسجَّل في settings MIDDLEWARE:
  'common.middleware.request_id.RequestIDMiddleware'
"""

import uuid
import logging

logger = logging.getLogger("hotel_saas")


class RequestIDMiddleware:
    """
    Middleware لتوليد X-Request-ID لكل HTTP request.

    يُضيف:
        request.request_id  → UUID string متاح في الـ views والـ logs
        response['X-Request-ID'] → Header في الـ response للـ debugging

    Args:
        get_response: Callable للـ view التالي في السلسلة
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # توليد UUID فريد لكل request
        # نتحقق أولاً إذا كان الـ client بعث X-Request-ID (لـ proxy servers)
        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        request.request_id = request_id

        # تسجيل بداية الـ request
        logger.debug(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
            },
        )

        # تنفيذ الـ view
        response = self.get_response(request)

        # إضافة request_id لـ response headers
        response["X-Request-ID"] = request_id

        return response
