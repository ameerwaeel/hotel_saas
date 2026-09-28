"""
common/exceptions/handlers.py
==============================
المسار: common/exceptions/handlers.py
الوظيفة: Exception handler مخصص لـ DRF يضمن أن كل الأخطاء ترجع بنفس شكل JSON.

الشكل الموحد للأخطاء:
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",           // كود الخطأ (snake_case)
        "message": "رسالة الخطأ الرئيسية",   // رسالة قابلة للعرض للمستخدم
        "details": {...},                      // تفاصيل الخطأ (validation fields مثلاً)
        "request_id": "uuid-string"           // من RequestIDMiddleware للـ debugging
    }
}

الأكواد المستخدمة:
  - VALIDATION_ERROR (400)
  - AUTHENTICATION_FAILED (401) — فارق عن PERMISSION_DENIED (403)
  - PERMISSION_DENIED (403)
  - NOT_FOUND (404)
  - METHOD_NOT_ALLOWED (405)
  - INTERNAL_SERVER_ERROR (500)

🎯 مهم: نفرق بين 401 و 403:
  - 401: المستخدم غير مسجل (IsAuthenticated فشل)
  - 403: مسجل لكن ليس له صلاحية (HasHotelPermission فشل)
"""

import logging
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    NotFound,
    ValidationError,
    MethodNotAllowed,
    Throttled,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("hotel_saas")


def custom_exception_handler(exc, context):
    """
    DRF exception handler مخصص.

    يُعرَّف في REST_FRAMEWORK settings:
      'EXCEPTION_HANDLER': 'common.exceptions.handlers.custom_exception_handler'

    يُحوِّل كل الأخطاء لشكل JSON موحد مع:
      - request_id من RequestIDMiddleware
      - تفريق واضح بين 401 و 403
      - logging تلقائي للأخطاء

    Args:
        exc: الاستثناء المُثار
        context: context الطلب (request, view, kwargs)

    Returns:
        Response بالشكل الموحد أو None إذا كان الاستثناء غير مدعوم
    """
    request = context.get("request")

    # تحويل Django exceptions لـ DRF exceptions
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = DRFPermissionDenied()
    elif isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    # استدعاء الـ handler الأصلي لمعالجة الـ DRF exceptions
    response = exception_handler(exc, context)

    if response is not None:
        # استخراج request_id من الـ request (يُضاف بواسطة RequestIDMiddleware)
        request_id = getattr(request, "request_id", None) if request else None

        # تحديد error code
        error_code = _get_error_code(exc)

        # تحديد رسالة الخطأ الرئيسية
        message = _get_error_message(exc)

        # تحديد التفاصيل
        details = _get_error_details(response.data)

        # logging الأخطاء (500 فقط كـ ERROR، باقيها WARNING)
        if response.status_code >= 500:
            logger.error(
                "Server error",
                extra={
                    "request_id": request_id,
                    "error_code": error_code,
                    "status_code": response.status_code,
                    "path": request.path if request else None,
                },
                exc_info=True,
            )
        elif response.status_code >= 400:
            logger.warning(
                "Client error",
                extra={
                    "request_id": request_id,
                    "error_code": error_code,
                    "status_code": response.status_code,
                    "path": request.path if request else None,
                },
            )

        # بناء الـ response الموحد
        response.data = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
                "request_id": request_id,
            },
        }

    return response


def _get_error_code(exc: APIException) -> str:
    """تحديد error code من نوع الاستثناء."""
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return "AUTHENTICATION_FAILED"
    elif isinstance(exc, DRFPermissionDenied):
        return "PERMISSION_DENIED"
    elif isinstance(exc, NotFound):
        return "NOT_FOUND"
    elif isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    elif isinstance(exc, MethodNotAllowed):
        return "METHOD_NOT_ALLOWED"
    elif isinstance(exc, Throttled):
        return "THROTTLED"
    elif hasattr(exc, "default_code") and exc.default_code:
        return exc.default_code.upper()
    else:
        return "INTERNAL_SERVER_ERROR"


def _get_error_message(exc: APIException) -> str:
    """استخراج رسالة الخطأ الرئيسية."""
    if hasattr(exc, "detail"):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        elif isinstance(detail, list) and detail:
            first = detail[0]
            return str(first) if not hasattr(first, "string") else first.string
        elif isinstance(detail, dict):
            # أول خطأ في الـ dict
            for key, value in detail.items():
                if isinstance(value, list) and value:
                    return f"{key}: {value[0]}"
                return f"{key}: {value}"
    return str(exc)


def _get_error_details(data) -> dict | list | None:
    """استخراج تفاصيل الخطأ للعرض (validation errors مثلاً)."""
    if isinstance(data, dict):
        # إزالة المفاتيح غير المفيدة
        if "detail" in data and len(data) == 1:
            return None
        return {k: v for k, v in data.items() if k != "detail"}
    elif isinstance(data, list):
        return data
    return None
