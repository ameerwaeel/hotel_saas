"""
rooms/selectors.py
==================
المسار: rooms/selectors.py
Phase: 4 — Master Data

الـ Selectors هي طبقة Query الخاصة بالـ rooms app.
كل query للـ database تمر هنا — الـ Views لا تعمل queries مباشرة.

مبدأ Selector Layer:
  - كل function تقبل hotel كـ context
  - تطبق select_related / prefetch_related لمنع N+1
  - تُرجع QuerySet (لا evaluate فوري) إلا عند الحاجة
"""

from django.db.models import QuerySet, Prefetch
from rooms.models import Language, HotelLanguage, BookingSource, RoomType, Room, RoomTypeTranslation, RoomStatus


# ---------------------------------------------------------------------------
# Language Selectors
# ---------------------------------------------------------------------------

def get_all_active_languages() -> QuerySet:
    """جميع اللغات النشطة في النظام."""
    return Language.objects.filter(is_active=True).order_by("name")


def get_hotel_languages(hotel) -> QuerySet:
    """
    لغات فندق معين.
    N+1 safe: select_related("language").
    """
    return (
        HotelLanguage.objects
        .filter(hotel=hotel)
        .select_related("language")
        .order_by("-is_default", "language__name")
    )


def get_hotel_default_language(hotel):
    """اللغة الافتراضية للفندق (None إذا لم تُحدَّد)."""
    return (
        HotelLanguage.objects
        .filter(hotel=hotel, is_default=True)
        .select_related("language")
        .first()
    )


# ---------------------------------------------------------------------------
# BookingSource Selectors
# ---------------------------------------------------------------------------

def get_booking_sources(hotel) -> QuerySet:
    """مصادر الحجز لفندق معين — نشطة فقط."""
    return BookingSource.objects.for_hotel(hotel).filter(is_active=True)


def get_all_booking_sources(hotel) -> QuerySet:
    """جميع مصادر الحجز (نشطة وغير نشطة) — للـ Admin."""
    return BookingSource.objects.for_hotel(hotel)


# ---------------------------------------------------------------------------
# RoomType Selectors
# ---------------------------------------------------------------------------

def get_room_types(hotel) -> QuerySet:
    """
    أنواع الغرف لفندق معين مع ترجماتها.

    ⚠️ N+1 Prevention:
       prefetch_related("translations__language") يجلب كل الترجمات
       في query واحد إضافي (لا N queries).
    """
    return (
        RoomType.objects
        .for_hotel(hotel)
        .filter(is_active=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=RoomTypeTranslation.objects.select_related("language"),
            )
        )
    )


def get_room_type_by_id(hotel, room_type_id) -> RoomType:
    """نوع غرفة محدد داخل فندق — يرفع 404 إذا لم يوجد."""
    return (
        RoomType.objects
        .for_hotel(hotel)
        .prefetch_related("translations__language")
        .get(id=room_type_id)
    )


# ---------------------------------------------------------------------------
# Room Selectors
# ---------------------------------------------------------------------------

def get_rooms(hotel, status=None, room_type_id=None, floor=None) -> QuerySet:
    """
    غرف الفندق مع فلترة اختيارية.

    ⚠️ N+1 Prevention:
       select_related("room_type") — يجلب RoomType في نفس query.

    Args:
        hotel: الفندق
        status: فلتر على حالة الغرفة
        room_type_id: فلتر على نوع الغرفة
        floor: فلتر على الطابق
    """
    qs = (
        Room.objects
        .for_hotel(hotel)
        .filter(is_active=True)
        .select_related("room_type")
    )
    if status:
        qs = qs.filter(status=status)
    if room_type_id:
        qs = qs.filter(room_type_id=room_type_id)
    if floor is not None:
        qs = qs.filter(floor=floor)
    return qs


def get_available_rooms(hotel, room_type_id=None) -> QuerySet:
    """غرف متاحة فقط (status=AVAILABLE)."""
    return get_rooms(hotel, status=RoomStatus.AVAILABLE, room_type_id=room_type_id)


def get_room_by_id(hotel, room_id) -> Room:
    """غرفة محددة داخل فندق — يرفع DoesNotExist إذا لم توجد."""
    return (
        Room.objects
        .for_hotel(hotel)
        .select_related("room_type")
        .get(id=room_id)
    )
