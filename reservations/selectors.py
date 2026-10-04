"""
reservations/selectors.py
=========================
المسار: reservations/selectors.py
Phase: 5 — Reservations + Availability Engine

⚠️ Availability Query هي أهم query في المشروع:
   تستخدم overlap query بدل per-day table.
"""

from django.db.models import QuerySet, Prefetch, Q
from reservations.models import Reservation, ReservationRoom, ReservationStatus
from rooms.models import Room, RoomStatus


# ---------------------------------------------------------------------------
# Availability Engine
# ---------------------------------------------------------------------------

def get_available_rooms_for_dates(hotel, check_in, check_out, room_type_id=None) -> QuerySet:
    """
    ⚠️ أهم function في Phase 5 — Availability Engine.

    تحسب الغرف المتاحة للتواريخ المطلوبة باستخدام Overlap Query.
    
    الـ Algorithm:
    1. ابدأ بكل الغرف النشطة المتاحة في الفندق
    2. استثنِ الغرف التي عليها حجوزات تتداخل مع التواريخ المطلوبة
    
    Overlap Condition:
      check_in_requested < check_out_existing AND check_out_requested > check_in_existing
      (أي تداخل زمني بأي شكل)

    ⚠️ Composite index (room_id, check_in, check_out) على ReservationRoom يجعل هذا سريعاً.

    Args:
        hotel: الفندق
        check_in: تاريخ الوصول المطلوب
        check_out: تاريخ المغادرة المطلوب
        room_type_id: فلتر على نوع الغرفة (اختياري)
    """
    # الغرف المحجوزة في نفس الفترة (overlap)
    occupied_room_ids = (
        ReservationRoom.objects
        .filter(
            hotel=hotel,
            reservation__status__in=[
                ReservationStatus.CONFIRMED,
                ReservationStatus.CHECKED_IN,
            ],
            deleted_at__isnull=True,  # لا نحسب السجلات المحذوفة ناعمياً
        )
        .filter(
            # Overlap condition: الطلب يتداخل مع الحجز الموجود
            check_in__lt=check_out,
            check_out__gt=check_in,
        )
        .values_list("room_id", flat=True)
    )

    # الغرف المتاحة = كل الغرف - الغرف المحجوزة
    qs = (
        Room.objects
        .for_hotel(hotel)
        .filter(is_active=True, status=RoomStatus.AVAILABLE)
        .exclude(id__in=occupied_room_ids)
        .select_related("room_type")
    )

    if room_type_id:
        qs = qs.filter(room_type_id=room_type_id)

    return qs


def is_room_available(hotel, room, check_in, check_out, exclude_reservation_id=None) -> bool:
    """
    التحقق من توفر غرفة محددة في فترة معينة.
    
    ⚠️ تُستخدم مع select_for_update() في Service Layer لمنع Race Conditions.
    
    Args:
        exclude_reservation_id: تجاهل حجز محدد (لتعديل حجز قائم)
    """
    qs = (
        ReservationRoom.objects
        .filter(
            room=room,
            reservation__status__in=[
                ReservationStatus.CONFIRMED,
                ReservationStatus.CHECKED_IN,
            ],
            deleted_at__isnull=True,
            check_in__lt=check_out,
            check_out__gt=check_in,
        )
    )
    if exclude_reservation_id:
        qs = qs.exclude(reservation_id=exclude_reservation_id)

    return not qs.exists()


# ---------------------------------------------------------------------------
# Reservation Selectors
# ---------------------------------------------------------------------------

def get_reservations(hotel, status=None, customer_id=None, check_in_from=None,
                     check_in_to=None) -> QuerySet:
    """
    قائمة الحجوزات مع N+1 prevention.

    ⚠️ N+1 Safe:
       select_related("customer", "booking_source", "created_by")
       prefetch_related("reservation_rooms__room__room_type")
    """
    qs = (
        Reservation.objects
        .for_hotel(hotel)
        .select_related("customer", "booking_source", "created_by")
        .prefetch_related(
            Prefetch(
                "reservation_rooms",
                queryset=ReservationRoom.objects
                    .filter(deleted_at__isnull=True)
                    .select_related("room__room_type"),
            )
        )
    )

    if status:
        qs = qs.filter(status=status)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if check_in_from:
        qs = qs.filter(check_in__gte=check_in_from)
    if check_in_to:
        qs = qs.filter(check_in__lte=check_in_to)

    return qs


def get_reservation_by_id(hotel, reservation_id) -> Reservation:
    """حجز محدد مع كل بياناته."""
    return (
        Reservation.objects
        .for_hotel(hotel)
        .select_related("customer", "booking_source", "created_by")
        .prefetch_related("reservation_rooms__room__room_type")
        .get(id=reservation_id)
    )
