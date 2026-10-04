"""
reservations/services.py
========================
المسار: reservations/services.py
Phase: 5 — Reservations + Availability Engine + Room Upgrade

⚠️ أهم Service في المشروع:
   - select_for_update() + transaction.atomic() لمنع Race Conditions
   - State Machine enforcement
   - ReservationRoomChange history tracking
   - CheckoutService creates RoomCleaning (Phase 7 integration)
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from reservations.models import (
    Reservation, ReservationRoom, ReservationRoomChange,
    ReservationStatus, VALID_TRANSITIONS
)
from reservations.selectors import is_room_available
from rooms.models import Room, RoomStatus


class ReservationService:
    """
    Service Layer للحجوزات.
    كل عملية تغيير تمر هنا — لا في الـ Views أو Serializers.
    """

    @staticmethod
    @transaction.atomic
    def create(
        hotel,
        customer,
        check_in,
        check_out,
        rooms_data: list,   # [{"room_id": uuid, "adults": 1, "children": 0, "notes": ""}]
        booking_source=None,
        adults: int = 1,
        children: int = 0,
        currency: str = "USD",
        special_requests: str = "",
        internal_notes: str = "",
        created_by=None,
    ) -> Reservation:
        """
        إنشاء حجز جديد مع التحقق من توفر الغرف.

        ⚠️ Race Condition Prevention:
           نستخدم select_for_update() على الغرف قبل التحقق من التوفر.
           هذا يقفل الغرفة على مستوى الـ DB داخل نفس الـ transaction،
           مما يمنع حجز نفس الغرفة من مستخدمين في نفس اللحظة.

        Args:
            rooms_data: قائمة الغرف المطلوبة مع تفاصيلها
        """
        # Validation: check_out > check_in
        if check_out <= check_in:
            raise ValidationError(_("Check-out date must be after check-in date."))

        if not rooms_data:
            raise ValidationError(_("At least one room must be selected."))

        # إنشاء الحجز الرئيسي أولاً
        reservation = Reservation(
            hotel=hotel,
            customer=customer,
            booking_source=booking_source,
            status=ReservationStatus.PENDING,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            currency=currency,
            special_requests=special_requests,
            internal_notes=internal_notes,
            created_by=created_by,
        )
        reservation.save()

        total_price = Decimal("0.00")

        for room_data in rooms_data:
            room_id = room_data["room_id"]
            room_check_in = room_data.get("check_in", check_in)
            room_check_out = room_data.get("check_out", check_out)
            room_adults = room_data.get("adults", 1)
            room_children = room_data.get("children", 0)
            room_notes = room_data.get("notes", "")

            # ⚠️ select_for_update: قفل الغرفة حتى نهاية الـ transaction
            try:
                room = (
                    Room.objects
                    .select_for_update()
                    .select_related("room_type")
                    .get(id=room_id, hotel=hotel, is_active=True)
                )
            except Room.DoesNotExist:
                raise ValidationError(_(f"Room not found in this hotel."))

            # ⚠️ التحقق من التوفر داخل نفس الـ transaction (بعد القفل)
            if not is_room_available(hotel, room, room_check_in, room_check_out):
                raise ValidationError(_(
                    f"Room {room.room_number} is not available "
                    f"for the selected dates."
                ))

            # حساب عدد الليالي والسعر
            nights = (room_check_out - room_check_in).days
            if nights <= 0:
                raise ValidationError(_("Invalid dates for room booking."))

            nightly_price = room.room_type.base_price
            room_total = nightly_price * nights
            total_price += room_total

            # إنشاء ReservationRoom
            ReservationRoom.objects.create(
                hotel=hotel,
                reservation=reservation,
                room=room,
                room_type=room.room_type,
                check_in=room_check_in,
                check_out=room_check_out,
                nightly_price=nightly_price,
                nights=nights,
                adults=room_adults,
                children=room_children,
                notes=room_notes,
            )

        # حفظ السعر الإجمالي
        reservation.total_price = total_price
        reservation.save(update_fields=["total_price"])

        return reservation

    @staticmethod
    @transaction.atomic
    def _transition(reservation: Reservation, new_status: str, **update_fields) -> Reservation:
        """
        تطبيق transition في الـ State Machine.
        يرفع ValidationError إذا كان الـ transition غير صالح.
        """
        current = reservation.status
        allowed = VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValidationError(_(
                f"Cannot transition from '{current}' to '{new_status}'. "
                f"Allowed: {allowed}"
            ))
        reservation.status = new_status
        for field, value in update_fields.items():
            setattr(reservation, field, value)
        reservation.save()
        return reservation

    @staticmethod
    def confirm(reservation: Reservation) -> Reservation:
        """تأكيد الحجز: pending → confirmed."""
        return ReservationService._transition(
            reservation,
            ReservationStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )

    @staticmethod
    def cancel(reservation: Reservation, reason: str = "") -> Reservation:
        """إلغاء الحجز: pending/confirmed → cancelled."""
        return ReservationService._transition(
            reservation,
            ReservationStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancellation_reason=reason,
        )

    @staticmethod
    def no_show(reservation: Reservation) -> Reservation:
        """No Show: confirmed → no_show."""
        return ReservationService._transition(
            reservation,
            ReservationStatus.NO_SHOW,
        )

    @staticmethod
    def check_in(reservation: Reservation) -> Reservation:
        """Check-in: confirmed → checked_in."""
        result = ReservationService._transition(
            reservation,
            ReservationStatus.CHECKED_IN,
            checked_in_at=timezone.now(),
        )
        # تحديث حالة الغرف إلى OCCUPIED
        room_ids = reservation.reservation_rooms.filter(
            deleted_at__isnull=True
        ).values_list("room_id", flat=True)
        Room.objects.filter(id__in=room_ids).update(status=RoomStatus.OCCUPIED)
        return result

    @staticmethod
    @transaction.atomic
    def check_out(reservation: Reservation) -> Reservation:
        """
        Check-out: checked_in → checked_out.
        
        ⚠️ Phase 7 Integration:
           بعد الـ checkout، نستدعي CheckoutService.create_cleaning_tasks()
           صراحةً (لا نستخدم signals المتشابكة).
        """
        result = ReservationService._transition(
            reservation,
            ReservationStatus.CHECKED_OUT,
            checked_out_at=timezone.now(),
        )

        # تحديث حالة الغرف إلى CLEANING
        room_ids = reservation.reservation_rooms.filter(
            deleted_at__isnull=True
        ).values_list("room_id", flat=True)
        Room.objects.filter(id__in=room_ids).update(status=RoomStatus.CLEANING)

        # ⚠️ Phase 7 Hook: إنشاء مهام تنظيف (سيُستدعى لاحقاً في Phase 7)
        ReservationService._create_cleaning_tasks(reservation, room_ids)

        # زيادة عداد إقامات العميل
        from customers.services import CustomerService
        CustomerService.increment_stays(reservation.customer)

        return result

    @staticmethod
    def _create_cleaning_tasks(reservation, room_ids):
        """
        Phase 7: إنشاء RoomCleaning tasks بعد الـ checkout.
        يُستدعى صراحةً من checkout() — لا signals متشابكة.
        """
        from housekeeping.models import RoomCleaning
        from rooms.models import Room
        for room_id in room_ids:
            try:
                room = Room.objects.get(id=room_id)
            except Room.DoesNotExist:
                continue
            RoomCleaning.objects.create(
                hotel=reservation.hotel,
                room=room,
                reservation=reservation,
                assigned_to=None,  # يُعيَّن لاحقاً من الـ housekeeping manager
            )

    @staticmethod
    @transaction.atomic
    def upgrade_room(
        reservation_room: ReservationRoom,
        new_room: Room,
        reason: str = "",
        changed_by=None,
    ) -> ReservationRoom:
        """
        ترقية/تغيير غرفة داخل حجز قائم.
        
        ⚠️ يحفظ سجل تاريخي في ReservationRoomChange.
        
        Args:
            reservation_room: ReservationRoom الحالية
            new_room: الغرفة الجديدة
            reason: سبب التغيير
            changed_by: من أجرى التغيير
        """
        reservation = reservation_room.reservation
        hotel = reservation.hotel

        # التحقق من أن الحجز في حالة تسمح بتغيير الغرفة
        if reservation.status not in [ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN]:
            raise ValidationError(_("Room upgrade only allowed for confirmed or checked-in reservations."))

        # قفل الغرفة الجديدة
        new_room_locked = (
            Room.objects
            .select_for_update()
            .select_related("room_type")
            .get(id=new_room.id)
        )

        # التحقق من توفر الغرفة الجديدة
        if not is_room_available(
            hotel, new_room_locked,
            reservation_room.check_in,
            reservation_room.check_out,
            exclude_reservation_id=reservation.id,
        ):
            raise ValidationError(_("New room is not available for the reservation dates."))

        old_room = reservation_room.room
        old_price = reservation_room.nightly_price
        new_price = new_room_locked.room_type.base_price
        price_diff = new_price - old_price

        # تسجيل التغيير
        ReservationRoomChange.objects.create(
            reservation_room=reservation_room,
            old_room=old_room,
            new_room=new_room_locked,
            old_price=old_price,
            new_price=new_price,
            price_difference=price_diff,
            reason=reason,
            changed_by=changed_by,
        )

        # تحديث ReservationRoom
        reservation_room.room = new_room_locked
        reservation_room.room_type = new_room_locked.room_type
        reservation_room.nightly_price = new_price
        reservation_room.save(update_fields=["room", "room_type", "nightly_price", "updated_at"])

        # إعادة حساب السعر الإجمالي للحجز
        total = sum(
            rr.nightly_price * rr.nights
            for rr in reservation.reservation_rooms.filter(deleted_at__isnull=True)
        )
        reservation.total_price = total
        reservation.save(update_fields=["total_price"])

        return reservation_room
