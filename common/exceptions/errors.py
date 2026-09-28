"""
common/exceptions/errors.py
============================
المسار: common/exceptions/errors.py
الوظيفة: Custom exceptions للـ business logic.
         كل exception ترث من APIException وتُرجع شكل JSON موحد.

الاستخدام:
    from common.exceptions.errors import TenantNotFoundError, PermissionDeniedError

    # في Service Layer:
    raise TenantNotFoundError("Hotel not found or inactive")

    # في Permission Class:
    raise PermissionDeniedError("You don't have permission: rooms.manage")
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class BusinessLogicError(APIException):
    """
    Base exception للـ business logic errors.
    ترفع HTTP 400 Bad Request بـ error code مخصص.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Business logic error occurred."
    default_code = "BUSINESS_LOGIC_ERROR"


class TenantNotFoundError(APIException):
    """
    المستخدم لا ينتمي لأي فندق نشط أو الفندق غير موجود.
    ترفع 403 وليس 404 لأن الـ resource قد يوجد لكن المستخدم ليس له وصول.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Active hotel context not found. Please select a hotel."
    default_code = "TENANT_NOT_FOUND"


class TenantAccessDeniedError(APIException):
    """
    محاولة الوصول لبيانات فندق آخر (cross-tenant isolation breach).
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Access to this hotel's resources is denied."
    default_code = "TENANT_ACCESS_DENIED"


class PermissionDeniedError(APIException):
    """
    المستخدم مسجل لكن ليس لديه صلاحية معينة.
    يختلف عن 401 — هنا المستخدم معروف لكن ممنوع.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have permission to perform this action."
    default_code = "PERMISSION_DENIED"


class FeatureNotAvailableError(APIException):
    """
    الميزة المطلوبة غير متاحة في خطة الاشتراك الحالية.
    يُستخدم في Phase 9 (SaaS Features).
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This feature is not available in your current subscription plan."
    default_code = "FEATURE_NOT_AVAILABLE"


class ResourceNotFoundError(APIException):
    """
    الـ resource المطلوب غير موجود داخل نطاق الفندق الحالي.
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "RESOURCE_NOT_FOUND"


class ConflictError(APIException):
    """
    تعارض في البيانات (مثلاً: double booking في Phase 5).
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict detected."
    default_code = "CONFLICT"


class InvalidStateTransitionError(BusinessLogicError):
    """
    محاولة انتقال غير صالح في الـ state machine (مثلاً: reservation status).
    يُستخدم في Phase 5.
    """
    default_detail = "Invalid state transition."
    default_code = "INVALID_STATE_TRANSITION"


class ClosedPeriodError(BusinessLogicError):
    """
    محاولة تعديل بيانات في فترة مُقفلة (DailyClosing في Phase 6).
    """
    default_detail = "This period has been closed and cannot be modified."
    default_code = "CLOSED_PERIOD"
