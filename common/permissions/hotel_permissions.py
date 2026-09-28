"""
common/permissions/hotel_permissions.py
=========================================
المسار: common/permissions/hotel_permissions.py
الوظيفة: DRF Permission Classes للـ RBAC.

Classes:
  ┌────────────────────────────────────────────────────────────────┐
  │  IsHotelMember     → مستخدم ينتمي للفندق النشط               │
  │  HasHotelPermission → مستخدم لديه صلاحية محددة في الفندق      │
  │  IsHotelAdmin      → مستخدم بدور Admin في الفندق              │
  │  IsPlatformAdmin   → admin على مستوى المنصة                    │
  └────────────────────────────────────────────────────────────────┘

مشاكل Django المحلولة:
  1. **401 vs 403 الفرق الحرج:**
     - 401: المستخدم غير مسجل (IsAuthenticated فشل)
     - 403: مسجل لكن ليس له صلاحية (HasHotelPermission فشل)
     - Django DRF الافتراضي يُرجع 403 في الحالتين — نحن نُصحح ذلك

  2. **N+1 في Permission Check:**
     - بدون cache: كل request → DB query للصلاحيات
     - مع cache: cache key "perms:{user_id}:{hotel_id}" → مرة واحدة كل 5 دقائق

  3. **Cache Invalidation:**
     - عند تغيير Role أو RolePermission → يُمسح الـ cache تلقائياً عبر signals
     - الـ signals معرَّفة في accounts/signals.py

الاستخدام في Views:
    from common.permissions.hotel_permissions import HasHotelPermission

    class RoomViewSet(ModelViewSet):
        permission_classes = [HasHotelPermission("rooms.manage")]

    # أو كـ list:
        permission_classes = [IsAuthenticated, HasHotelPermission("rooms.view")]
"""

import logging
from django.core.cache import cache
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.exceptions import NotAuthenticated

logger = logging.getLogger("hotel_saas")

# Cache settings للصلاحيات
PERMISSION_CACHE_TIMEOUT = 300  # 5 دقائق
PERMISSION_CACHE_KEY = "perms:{user_id}:{hotel_id}"


def get_user_permissions_for_hotel(user, hotel) -> list[str]:
    """
    جلب صلاحيات المستخدم في فندق معين مع caching.

    يُحل مشكلة N+1:
      بدون cache: Role → RolePermission → Permission (3 queries كل request)
      مع cache: من Redis مباشرة بعد أول request

    Cache Key: "perms:{user_id}:{hotel_id}"
    Timeout: 5 دقائق (يُمسح عند تغيير Role/RolePermission)

    Args:
        user: User instance
        hotel: Hotel instance

    Returns:
        List of permission codes (e.g., ["rooms.view", "rooms.manage"])
    """
    if not user or not hotel:
        return []

    # Platform admins لهم كل الصلاحيات
    if user.is_platform_admin or user.is_superuser:
        return ["*"]

    cache_key = PERMISSION_CACHE_KEY.format(user_id=user.id, hotel_id=hotel.id)
    permissions = cache.get(cache_key)

    if permissions is None:
        # جلب الصلاحيات من DB مع prefetch_related لتجنب N+1
        try:
            from accounts.models import HotelMembership
            membership = (
                HotelMembership.objects
                .select_related("role")
                .prefetch_related("role__rolepermissions__permission")
                .get(user=user, hotel=hotel, status="active")
            )

            if membership.role:
                permissions = membership.role.get_permission_codes()
            else:
                permissions = []

        except Exception:
            permissions = []

        # حفظ في cache
        cache.set(cache_key, permissions, PERMISSION_CACHE_TIMEOUT)
        logger.debug(
            "Permission cache miss — fetched from DB",
            extra={"user_id": str(user.id), "hotel_id": str(hotel.id), "count": len(permissions)},
        )

    return permissions


def invalidate_permission_cache(user_id, hotel_id):
    """
    مسح cache الصلاحيات لـ (user, hotel) بعد تغيير Role/RolePermission.

    يُستدعى من accounts/signals.py عند:
      - تغيير HotelMembership.role
      - إضافة/حذف RolePermission

    Args:
        user_id: UUID المستخدم
        hotel_id: UUID الفندق
    """
    cache_key = PERMISSION_CACHE_KEY.format(user_id=user_id, hotel_id=hotel_id)
    cache.delete(cache_key)
    logger.info(
        "Permission cache invalidated",
        extra={"user_id": str(user_id), "hotel_id": str(hotel_id)},
    )


class IsHotelMember(BasePermission):
    """
    يتحقق من أن المستخدم عضو نشط في الفندق النشط (request.hotel).

    يُرجع:
        403 إذا لم يكن المستخدم عضواً في الفندق
        403 إذا لم يكن هناك hotel context (request.hotel = None)

    الاستخدام:
        permission_classes = [IsAuthenticated, IsHotelMember]
    """

    message = "You are not an active member of this hotel."

    def has_permission(self, request, view) -> bool:
        # request.hotel يُحقن من TenantMiddleware
        hotel = getattr(request, "hotel", None)

        if not hotel:
            self.message = "No active hotel context. Please select a hotel."
            return False

        # Platform admins مسموح لهم دائماً
        if request.user.is_platform_admin or request.user.is_superuser:
            return True

        # تحقق من العضوية
        try:
            from accounts.models import HotelMembership
            return HotelMembership.objects.filter(
                user=request.user,
                hotel=hotel,
                status="active",
            ).exists()
        except Exception:
            return False


class HasHotelPermission(BasePermission):
    """
    يتحقق من أن المستخدم لديه صلاحية محددة في الفندق النشط.

    ⚠️ الفرق بين 401 و 403:
        - 401 (NotAuthenticated): يُرجعه IsAuthenticated إذا لم يكن المستخدم مسجلاً
        - 403 (PermissionDenied): يُرجعه HasHotelPermission إذا كان مسجلاً لكن بدون صلاحية

    الاستخدام:
        # كـ class مباشرة:
        class RoomViewSet(ModelViewSet):
            permission_classes = [HasHotelPermission("rooms.manage")]

        # مع IsAuthenticated:
        permission_classes = [IsAuthenticated, HasHotelPermission("rooms.view")]

    Args:
        permission_code: كود الصلاحية المطلوبة (مثلاً: "rooms.manage")
    """

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(self):
        """يسمح باستخدام HasHotelPermission("code") مباشرةً."""
        return self

    def has_permission(self, request, view) -> bool:
        """
        التحقق من الصلاحية مع caching.

        Returns:
            True: المستخدم لديه الصلاحية
            False: المستخدم ليس لديه الصلاحية (يُرجع 403)
        """
        # إذا لم يكن مسجلاً → 401 (IsAuthenticated يتعامل معه)
        if not request.user or not request.user.is_authenticated:
            return False

        hotel = getattr(request, "hotel", None)

        # Platform admins لهم كل الصلاحيات
        if request.user.is_platform_admin or request.user.is_superuser:
            return True

        if not hotel:
            self.message = "No active hotel context."
            return False

        # جلب الصلاحيات مع caching
        permissions = get_user_permissions_for_hotel(request.user, hotel)

        # "*" يعني كل الصلاحيات (platform admin)
        if "*" in permissions:
            return True

        has_perm = self.permission_code in permissions

        if not has_perm:
            self.message = f"You don't have permission: {self.permission_code}"
            logger.warning(
                "Permission denied",
                extra={
                    "user_id": str(request.user.id),
                    "hotel_id": str(hotel.id),
                    "required_permission": self.permission_code,
                    "request_id": getattr(request, "request_id", None),
                },
            )

        return has_perm


class IsHotelAdmin(HasHotelPermission):
    """
    Shortcut: يتحقق من صلاحية hotel.admin.
    يُستخدم للعمليات التي تتطلب مستوى Admin في الفندق.

    مثل:
        - إدارة الأدوار والصلاحيات
        - تعديل إعدادات الفندق
        - حذف بيانات مهمة
    """

    def __init__(self):
        super().__init__("hotel.admin")


class IsPlatformAdmin(BasePermission):
    """
    يتحقق من أن المستخدم هو platform admin (مستوى المنصة كلها).
    يُستخدم لـ endpoints إدارة المنصة.

    الاستخدام:
        permission_classes = [IsPlatformAdmin]
    """

    message = "Platform admin access required."

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_platform_admin or request.user.is_superuser)
        )
