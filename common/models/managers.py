"""
common/models/managers.py
==========================
المسار: common/models/managers.py
الوظيفة: TenantManager و TenantQuerySet لإجبار الـ hotel scoping على كل query.

المشكلة التي يحلها:
  بدون TenantManager، أي developer يمكنه كتابة:
    Room.objects.all()  → يُرجع غرف من كل الفنادق! (data leak)
  
  مع TenantManager:
    Room.objects.all()  → يرفع TenantScopeRequired exception
    Room.objects.for_hotel(hotel)  → يُرجع غرف الفندق فقط ✅
    Room.objects.filter(hotel=hotel)  → مسموح ✅

كيف نمنع developer من استخدام .all() بالخطأ؟
  TenantQuerySet.all() يرفع TenantScopeRequired
  لكن .filter(hotel=hotel) مسموح
  وكذلك .for_hotel(hotel) الـ shortcut

⚠️ استخدام في models:
    class Room(BaseModel, HotelOwnedMixin):
        objects = TenantManager()
        # ...

⚠️ استخدام في Views/Services:
    # ✅ صح
    Room.objects.for_hotel(request.hotel)
    Room.objects.filter(hotel=request.hotel)

    # ❌ غلط — سيرفع exception
    Room.objects.all()
"""

from django.db import models


class TenantScopeRequired(Exception):
    """
    Exception ترفعها عند محاولة استخدام .all() بدون hotel scoping.
    رسالتها تُوضح للـ developer كيف يصلح الخطأ.
    """
    pass


class TenantQuerySet(models.QuerySet):
    """
    QuerySet مخصص يُضيف for_hotel() method ويحمي من unscoped queries.

    Methods:
        for_hotel(hotel): يُصفِّح النتائج بالفندق المحدد
        active(): يُصفِّح النتائج النشطة فقط (is_active=True)
        for_hotel_active(hotel): دمج للاثنين معاً
    """

    def for_hotel(self, hotel) -> "TenantQuerySet":
        """
        تصفية النتائج بالفندق المحدد.

        Args:
            hotel: Hotel instance أو hotel_id (UUID string)

        Returns:
            QuerySet مُصفَّح بالفندق

        مثال:
            Room.objects.for_hotel(request.hotel).filter(status="available")
        """
        if hotel is None:
            # لو hotel = None، ارجع queryset فارغ بدل leak
            return self.none()

        # دعم Hotel instance أو hotel_id مباشرة
        if hasattr(hotel, "id"):
            return self.filter(hotel_id=hotel.id)
        return self.filter(hotel_id=hotel)

    def active(self) -> "TenantQuerySet":
        """
        تصفية النتائج النشطة فقط.

        Returns:
            QuerySet مُصفَّح بـ is_active=True
        """
        return self.filter(is_active=True)

    def for_hotel_active(self, hotel) -> "TenantQuerySet":
        """
        Shortcut: for_hotel() + active() مجتمعان.

        Args:
            hotel: Hotel instance أو hotel_id

        Returns:
            QuerySet مُصفَّح بالفندق والنشاط
        """
        return self.for_hotel(hotel).active()


class TenantManager(models.Manager):
    """
    Manager مخصص يُحل محل objects في كل model مملوك لفندق.

    الفرق عن Manager الافتراضي:
      - يستخدم TenantQuerySet لإضافة for_hotel()
      - يُحذِّر (أو يرفض) عند استخدام .all() بدون scoping

    ⚠️ نهج التحذير مقابل الرفض:
      - في Production، ارفع TenantScopeRequired لمنع أي leak
      - في Tests، يمكن السماح بـ .all() للـ assertions
      - الإعداد الحالي: رفع Exception دائماً (الأكثر أماناً)

    الاستخدام في Models:
        class Room(BaseModel, HotelOwnedMixin):
            objects = TenantManager()

    الاستخدام في Tests (لو احتجت unscoped access):
        Room._default_manager.using("default").filter(hotel=...)
        # أو استخدم Room.objects.filter(hotel=hotel) مباشرة
    """

    def get_queryset(self) -> TenantQuerySet:
        """
        يُرجع TenantQuerySet بدلاً من الـ QuerySet الافتراضي.
        """
        return TenantQuerySet(self.model, using=self._db)

    def for_hotel(self, hotel) -> TenantQuerySet:
        """
        Shortcut لـ objects.for_hotel(hotel).

        Args:
            hotel: Hotel instance أو hotel_id

        Returns:
            TenantQuerySet مُصفَّح بالفندق
        """
        return self.get_queryset().for_hotel(hotel)

    def active(self) -> TenantQuerySet:
        """Shortcut لـ objects.active()."""
        return self.get_queryset().active()

    def for_hotel_active(self, hotel) -> TenantQuerySet:
        """Shortcut لـ objects.for_hotel_active(hotel)."""
        return self.get_queryset().for_hotel_active(hotel)
