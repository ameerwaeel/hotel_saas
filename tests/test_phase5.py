"""
tests/test_phase5.py
====================
Phase 5 Tests: Reservations + Availability Engine + State Machine + Race Condition

Tests:
  ✅ Create reservation with valid room
  ✅ Availability overlap query (confirmed/checked_in blocks)
  ✅ No overlap for cancelled/no_show reservations
  ✅ State machine valid transitions
  ✅ State machine invalid transitions
  ✅ Room upgrade with change history
  ✅ checkout → cleaning tasks created
  ✅ Tenant isolation on reservations
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from rooms.models import RoomType, Room, RoomStatus
from customers.models import Customer
from reservations.models import (
    Reservation, ReservationRoom, ReservationRoomChange, ReservationStatus
)
from reservations.services import ReservationService
from reservations.selectors import get_available_rooms_for_dates, is_room_available


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def room_type(db, hotel):
    return RoomType.objects.create(
        hotel=hotel, code="STD", base_price=Decimal("100.00"), max_occupancy=2
    )

@pytest.fixture
def room(db, hotel, room_type):
    return Room.objects.create(
        hotel=hotel, room_type=room_type, room_number="101",
        status=RoomStatus.AVAILABLE
    )

@pytest.fixture
def room2(db, hotel, room_type):
    return Room.objects.create(
        hotel=hotel, room_type=room_type, room_number="102",
        status=RoomStatus.AVAILABLE
    )

@pytest.fixture
def customer(db, hotel):
    return Customer.objects.create(
        hotel=hotel, first_name="Ali", last_name="Hassan", phone="+201000000001"
    )

@pytest.fixture
def checkin():
    return date.today() + timedelta(days=1)

@pytest.fixture
def checkout():
    return date.today() + timedelta(days=4)


# ---------------------------------------------------------------------------
# Availability Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAvailability:
    def test_room_available_when_no_bookings(self, hotel, room, checkin, checkout):
        available = list(get_available_rooms_for_dates(hotel, checkin, checkout))
        assert room in available

    def test_confirmed_reservation_blocks_room(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        available = list(get_available_rooms_for_dates(hotel, checkin, checkout))
        assert room not in available

    def test_cancelled_reservation_frees_room(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.cancel(res)
        available = list(get_available_rooms_for_dates(hotel, checkin, checkout))
        assert room in available

    def test_no_overlap_adjacent_dates(self, hotel, room, customer, admin_user):
        """حجز من يوم 1-3، يجب أن يوم 3-5 يكون متاح (لا تداخل)."""
        d1 = date.today() + timedelta(days=10)
        d2 = date.today() + timedelta(days=13)
        d3 = date.today() + timedelta(days=16)

        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=d1, check_out=d2,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)

        # d2→d3 shouldn't overlap with d1→d2
        available = list(get_available_rooms_for_dates(hotel, d2, d3))
        assert room in available

    def test_partial_overlap_blocks_room(self, hotel, room, customer, admin_user):
        """تداخل جزئي يجب أن يمنع الحجز."""
        d1 = date.today() + timedelta(days=5)
        d2 = date.today() + timedelta(days=10)
        d_overlap_start = date.today() + timedelta(days=8)
        d_overlap_end = date.today() + timedelta(days=12)

        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=d1, check_out=d2,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)

        available = list(get_available_rooms_for_dates(hotel, d_overlap_start, d_overlap_end))
        assert room not in available


# ---------------------------------------------------------------------------
# Reservation CRUD Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReservationCreate:
    def test_create_reservation(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        assert res.status == ReservationStatus.PENDING
        assert res.reservation_rooms.count() == 1
        assert res.total_price == Decimal("300.00")  # 100/night × 3 nights

    def test_create_fails_checkout_before_checkin(self, hotel, room, customer, admin_user):
        today = date.today()
        with pytest.raises(ValidationError):
            ReservationService.create(
                hotel=hotel, customer=customer,
                check_in=today + timedelta(days=5),
                check_out=today + timedelta(days=3),
                rooms_data=[{"room_id": str(room.id)}],
                created_by=admin_user
            )

    def test_create_fails_on_unavailable_room(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        # محاولة حجز نفس الغرفة في نفس الفترة
        customer2 = Customer.objects.create(
            hotel=hotel, first_name="B", last_name="B", phone="+201000000099"
        )
        with pytest.raises(ValidationError):
            ReservationService.create(
                hotel=hotel, customer=customer2,
                check_in=checkin, check_out=checkout,
                rooms_data=[{"room_id": str(room.id)}],
                created_by=admin_user
            )

    def test_pending_reservation_blocks_room(self, hotel, room, customer, checkin, checkout, admin_user):
        """الحجز المعلق (Pending) يجب أن يقفل الغرفة فوراً ويمنع حجزها مجدداً."""
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        assert res.status == ReservationStatus.PENDING

        customer2 = Customer.objects.create(
            hotel=hotel, first_name="Other", last_name="Guest", phone="+201000000088"
        )
        # محاولة حجز نفس الغرفة ونفس التواريخ والحجز الأول ما زال pending
        with pytest.raises(ValidationError) as excinfo:
            ReservationService.create(
                hotel=hotel, customer=customer2,
                check_in=checkin, check_out=checkout,
                rooms_data=[{"room_id": str(room.id)}],
                created_by=admin_user
            )
        assert "not available" in str(excinfo.value)



# ---------------------------------------------------------------------------
# State Machine Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStateMachine:
    def test_pending_to_confirmed(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        confirmed = ReservationService.confirm(res)
        assert confirmed.status == ReservationStatus.CONFIRMED
        assert confirmed.confirmed_at is not None

    def test_pending_to_cancelled(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        cancelled = ReservationService.cancel(res, reason="Changed mind")
        assert cancelled.status == ReservationStatus.CANCELLED
        assert cancelled.cancellation_reason == "Changed mind"

    def test_confirmed_to_checked_in(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        checked_in = ReservationService.check_in(res)
        assert checked_in.status == ReservationStatus.CHECKED_IN
        room.refresh_from_db()
        assert room.status == RoomStatus.OCCUPIED

    def test_checked_in_to_checked_out(self, hotel, room, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        ReservationService.check_in(res)
        checked_out = ReservationService.check_out(res)
        assert checked_out.status == ReservationStatus.CHECKED_OUT
        room.refresh_from_db()
        assert room.status == RoomStatus.CLEANING

    def test_invalid_transition_raises_error(self, hotel, room, customer, checkin, checkout, admin_user):
        """PENDING → checked_in مباشرة يجب أن يفشل."""
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        with pytest.raises(ValidationError):
            ReservationService.check_in(res)

    def test_checkout_creates_cleaning_task(self, hotel, room, customer, checkin, checkout, admin_user):
        """checkout يجب أن ينشئ RoomCleaning task."""
        from housekeeping.models import RoomCleaning
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        ReservationService.check_in(res)
        ReservationService.check_out(res)
        assert RoomCleaning.objects.filter(room=room, reservation=res).exists()

    def test_checkout_increments_customer_stays(self, hotel, room, customer, checkin, checkout, admin_user):
        initial_stays = customer.total_stays
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        ReservationService.check_in(res)
        ReservationService.check_out(res)
        customer.refresh_from_db()
        assert customer.total_stays == initial_stays + 1


# ---------------------------------------------------------------------------
# Room Upgrade Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRoomUpgrade:
    def test_upgrade_room_creates_change_record(self, hotel, room, room2, customer, checkin, checkout, admin_user):
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        res_room = res.reservation_rooms.first()
        ReservationService.upgrade_room(
            reservation_room=res_room, new_room=room2,
            reason="Guest upgrade request", changed_by=admin_user
        )
        assert ReservationRoomChange.objects.filter(
            reservation_room=res_room, old_room=room, new_room=room2
        ).exists()

    def test_upgrade_room_updates_price(self, hotel, room, room2, customer, checkin, checkout, admin_user):
        room2.room_type.base_price = Decimal("150.00")
        room2.room_type.save()
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        ReservationService.confirm(res)
        res_room = res.reservation_rooms.first()
        ReservationService.upgrade_room(res_room, room2, changed_by=admin_user)
        res_room.refresh_from_db()
        assert res_room.nightly_price == Decimal("150.00")


# ---------------------------------------------------------------------------
# Tenant Isolation Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReservationTenantIsolation:
    def test_reservations_scoped_to_hotel(self, hotel, hotel2, room, customer, checkin, checkout, admin_user):
        from reservations.selectors import get_reservations
        res = ReservationService.create(
            hotel=hotel, customer=customer, check_in=checkin, check_out=checkout,
            rooms_data=[{"room_id": str(room.id)}], created_by=admin_user
        )
        hotel2_reservations = list(get_reservations(hotel2))
        assert res not in hotel2_reservations
