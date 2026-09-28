"""
common/middleware/tenant.py
============================
المسار: common/middleware/tenant.py
الوظيفة: Tenant Middleware يُحقن request.hotel من JWT token.

كيف يعمل:
  1. يقرأ hotel_id من JWT payload (يُضاف لـ token في Phase 3 عند تحديد الفندق النشط)
  2. يجلب Hotel object ويضعه في request.hotel
  3. إذا لم يكن هناك hotel_id في الـ token، يضع request.hotel = None
     (الـ views والـ permissions ستتعامل معه)

⚠️ مهم: هذا الـ middleware لا يرفض الطلبات بنفسه — هذا دور الـ Permission Classes.
   الـ middleware يُحقن فقط، والـ permissions تتحقق.

⚠️ مشكلة Django المعروفة مع Tenant Leakage:
   بدون هذا الـ middleware، كل view لازم تجلب hotel يدوياً من الـ request.
   إذا نسي أي developer ذلك → data leakage بين الفنادق.
   الحل: الـ middleware يُحقن دائماً، والـ TenantManager يُجبر على الـ scoping.

مُسجَّل في settings MIDDLEWARE بعد AuthenticationMiddleware:
  'common.middleware.tenant.TenantMiddleware'
"""

import logging
from django.core.cache import cache

logger = logging.getLogger("hotel_saas")

# Cache key لتخزين hotel objects (تجنب DB query في كل request)
HOTEL_CACHE_TIMEOUT = 300  # 5 minutes
HOTEL_CACHE_KEY = "hotel:{hotel_id}"


class TenantMiddleware:
    """
    Middleware لحقن request.hotel من JWT token.

    الـ hotel_id يُستخرج من:
      1. JWT payload claim "hotel_id" (يُضاف في Phase 3)
      2. Session (fallback للـ browsable API)

    Attributes مُضافة للـ request:
        request.hotel → Hotel instance أو None

    Args:
        get_response: Callable للـ view التالي
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تهيئة request.hotel بـ None افتراضياً
        request.hotel = None

        # محاولة استخراج hotel_id من الـ JWT token
        # ⚠️ في Phase 2: الـ JWT لم يُطبَّق بعد، سيكون hotel = None دائماً
        # ⚠️ في Phase 3: سيُضاف hotel_id لـ JWT payload ويُستخرج هنا
        hotel_id = self._extract_hotel_id_from_request(request)

        if hotel_id:
            request.hotel = self._get_hotel(hotel_id)

        response = self.get_response(request)
        return response

    def _extract_hotel_id_from_request(self, request) -> str | None:
        """
        استخراج hotel_id من مصادر مختلفة.

        Priority:
          1. JWT payload claim (Phase 3+)
          2. Session key (fallback)
          3. None إذا لم يوجد

        ⚠️ Note: الـ JWT لم يُفكَّك هنا لأن ذلك دور rest_framework_simplejwt.
            في Phase 3 سنُضيف custom claim وسنقرأه من request.auth.
        """
        # Phase 3+: قراءة hotel_id من JWT claims
        # request.auth يكون متاحاً بعد authentication middleware
        # لكن في مرحلة الـ middleware، الـ DRF authentication لم يُطبَّق بعد
        # لذلك نستخدم session كـ fallback
        if hasattr(request, "session") and "active_hotel_id" in request.session:
            return request.session.get("active_hotel_id")

        return None

    def _get_hotel(self, hotel_id: str):
        """
        جلب Hotel object من الـ cache أو DB.

        مشكلة Django المعروفة: لو جلبنا الـ Hotel من DB في كل request
        → overhead كبير. الحل: cache لمدة 5 دقائق.

        Args:
            hotel_id: UUID الفندق

        Returns:
            Hotel instance أو None إذا لم يوجد/غير نشط
        """
        cache_key = HOTEL_CACHE_KEY.format(hotel_id=hotel_id)
        hotel = cache.get(cache_key)

        if hotel is None:
            try:
                from tenants.models import Hotel
                hotel = Hotel.objects.get(id=hotel_id, is_active=True)
                cache.set(cache_key, hotel, HOTEL_CACHE_TIMEOUT)
            except Exception:
                # Hotel غير موجود أو غير نشط
                logger.warning(
                    "Hotel not found or inactive",
                    extra={"hotel_id": hotel_id},
                )
                return None

        return hotel
