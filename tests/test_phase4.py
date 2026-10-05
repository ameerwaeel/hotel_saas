"""
tests/test_phase4.py
====================
Phase 4 Tests: Rooms, Customers, Employees, Languages, BookingSources

Tests:
  ✅ Room CRUD (tenant-scoped)
  ✅ RoomType with translations (N+1 safe)
  ✅ room_number unique per hotel (cross-hotel allowed)
  ✅ Customer search (name/phone/email)
  ✅ Employee links to User + HotelMembership validation
  ✅ BookingSource CRUD
  ✅ HotelLanguage (set default)
  ✅ Cross-tenant isolation
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from rooms.models import Language, HotelLanguage, BookingSource, RoomType, RoomTypeTranslation, Room, RoomStatus
from rooms.services import LanguageService, HotelLanguageService, BookingSourceService, RoomTypeService, RoomService
from rooms.selectors import get_rooms, get_room_types, get_available_rooms
from customers.models import Customer, Employee, Department
from customers.services import CustomerService, EmployeeService
from customers.selectors import get_customers, get_employees


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def language_en(db):
    return Language.objects.create(code="en", name="English", native_name="English", is_rtl=False)

@pytest.fixture
def language_ar(db):
    return Language.objects.create(code="ar", name="Arabic", native_name="العربية", is_rtl=True)

@pytest.fixture
def room_type(db, hotel):
    return RoomType.objects.create(
        hotel=hotel, code="STD", base_price=Decimal("100.00"), max_occupancy=2
    )

@pytest.fixture
def room(db, hotel, room_type):
    return Room.objects.create(
        hotel=hotel, room_type=room_type, room_number="101", floor=1,
        status=RoomStatus.AVAILABLE,
    )

@pytest.fixture
def customer(db, hotel):
    return Customer.objects.create(
        hotel=hotel, first_name="Ahmed", last_name="Ali",
        phone="+201001234567", email="ahmed@test.com",
    )

@pytest.fixture
def booking_source(db, hotel):
    return BookingSource.objects.create(hotel=hotel, name="Walk-in", is_online=False)


# ---------------------------------------------------------------------------
# Language Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLanguage:
    def test_create_language(self):
        lang = LanguageService.create("fr", "French", "Français", is_rtl=False)
        assert lang.code == "fr"
        assert lang.is_rtl is False

    def test_language_code_unique(self):
        Language.objects.create(code="de", name="German")
        with pytest.raises(Exception):
            Language.objects.create(code="de", name="German 2")

    def test_hotel_language_set_default(self, db, hotel, language_en, language_ar):
        hl_en = HotelLanguageService.add_language(hotel, "en", is_default=True)
        hl_ar = HotelLanguageService.add_language(hotel, "ar", is_default=False)
        assert hl_en.is_default is True
        assert hl_ar.is_default is False

    def test_hotel_language_change_default(self, db, hotel, language_en, language_ar):
        HotelLanguageService.add_language(hotel, "en", is_default=True)
        HotelLanguageService.add_language(hotel, "ar", is_default=True)  # should un-default en
        en_hotel_lang = HotelLanguage.objects.get(hotel=hotel, language=language_en)
        ar_hotel_lang = HotelLanguage.objects.get(hotel=hotel, language=language_ar)
        assert en_hotel_lang.is_default is False
        assert ar_hotel_lang.is_default is True


# ---------------------------------------------------------------------------
# RoomType Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRoomType:
    def test_create_room_type(self, hotel, language_en, language_ar):
        rt = RoomTypeService.create(
            hotel=hotel, code="DLX", base_price=Decimal("200.00"),
            translations=[
                {"language_code": "en", "name": "Deluxe", "description": "Deluxe room"},
                {"language_code": "ar", "name": "ديلوكس", "description": "غرفة ديلوكس"},
            ]
        )
        assert rt.code == "DLX"
        assert RoomTypeTranslation.objects.filter(room_type=rt).count() == 2

    def test_room_type_code_unique_per_hotel(self, hotel):
        RoomType.objects.create(hotel=hotel, code="STD", base_price=Decimal("100.00"))
        with pytest.raises(Exception):
            RoomType.objects.create(hotel=hotel, code="STD", base_price=Decimal("150.00"))

    def test_room_type_code_allowed_different_hotels(self, hotel, hotel2):
        RoomType.objects.create(hotel=hotel, code="STD", base_price=Decimal("100.00"))
        rt2 = RoomType.objects.create(hotel=hotel2, code="STD", base_price=Decimal("120.00"))
        assert rt2.id is not None  # OK — different hotels

    def test_get_room_types_n1_safe(self, hotel, room_type, language_en, django_assert_num_queries):
        """Selector يجب أن يجلب translations في query واحد إضافي فقط."""
        RoomTypeTranslation.objects.create(
            room_type=room_type, language=language_en, name="Standard"
        )
        with django_assert_num_queries(2):  # 1 for RoomType + 1 prefetch for translations
            rts = list(get_room_types(hotel).prefetch_related("translations"))
            for rt in rts:
                _ = list(rt.translations.all())


# ---------------------------------------------------------------------------
# Room Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRoom:
    def test_create_room(self, hotel, room_type):
        room = RoomService.create(hotel, room_type.id, "201", floor=2)
        assert room.room_number == "201"
        assert room.status == RoomStatus.AVAILABLE

    def test_room_number_unique_per_hotel(self, hotel, room_type):
        RoomService.create(hotel, room_type.id, "101")
        with pytest.raises(Exception):
            RoomService.create(hotel, room_type.id, "101")

    def test_room_number_allowed_different_hotels(self, hotel, hotel2, room_type):
        """نفس رقم الغرفة مسموح في فنادق مختلفة."""
        RoomService.create(hotel, room_type.id, "101")
        rt2 = RoomType.objects.create(hotel=hotel2, code="STD", base_price=Decimal("100.00"))
        r2 = RoomService.create(hotel2, rt2.id, "101")
        assert r2.id is not None

    def test_update_room_status(self, hotel, room):
        updated = RoomService.update_status(room, "occupied", check_blocking=False)
        assert updated.status == "occupied"

    def test_get_rooms_scoped_to_hotel(self, hotel, hotel2, room):
        rt2 = RoomType.objects.create(hotel=hotel2, code="STD", base_price=Decimal("100.00"))
        Room.objects.create(hotel=hotel2, room_type=rt2, room_number="999")
        rooms = get_rooms(hotel)
        assert all(r.hotel_id == hotel.id for r in rooms)

    def test_get_available_rooms(self, hotel, room, room_type):
        """فقط الغرف المتاحة تظهر."""
        room2 = Room.objects.create(
            hotel=hotel, room_type=room_type, room_number="102",
            status=RoomStatus.OCCUPIED
        )
        available = list(get_available_rooms(hotel))
        ids = [r.id for r in available]
        assert room.id in ids
        assert room2.id not in ids


# ---------------------------------------------------------------------------
# Customer Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCustomer:
    def test_create_customer(self, hotel):
        c = CustomerService.create(
            hotel, "Sara", "Hassan", phone="+201009999999", email="sara@test.com"
        )
        assert c.first_name == "Sara"
        assert c.hotel == hotel

    def test_create_customer_with_date_of_birth(self, hotel):
        from datetime import date
        c = CustomerService.create(
            hotel, "Ahmed", "Hassan", phone="+201001234567",
            email="ahmed@example.com", nationality="EG",
            id_type="national_id", id_number="12345678901234",
            date_of_birth=date(1990, 1, 15), vip_status=False
        )
        assert c.date_of_birth == date(1990, 1, 15)
        assert c.id_number == "12345678901234"

    def test_customer_search_by_phone(self, hotel, customer):
        results = list(get_customers(hotel, search=customer.phone))
        assert customer in results

    def test_customer_search_by_name(self, hotel, customer):
        results = list(get_customers(hotel, search="Ahmed"))
        assert customer in results

    def test_customer_cross_tenant_isolation(self, hotel, hotel2, customer):
        results = list(get_customers(hotel2))
        assert customer not in results

    def test_vip_filter(self, hotel):
        vip = CustomerService.create(hotel, "VIP", "Guest", phone="+201000000001", vip_status=True)
        normal = CustomerService.create(hotel, "Normal", "Guest", phone="+201000000002")
        vips = list(get_customers(hotel, vip_only=True))
        assert vip in vips
        assert normal not in vips

    def test_increment_stays(self, hotel, customer):
        original = customer.total_stays
        CustomerService.increment_stays(customer)
        customer.refresh_from_db()
        assert customer.total_stays == original + 1


# ---------------------------------------------------------------------------
# Employee Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmployee:
    def test_create_employee_requires_membership(self, hotel, admin_user):
        """موظف يحتاج HotelMembership نشطة."""
        from accounts.models import HotelMembership, MembershipStatus
        from customers.models import Employee
        # بدون membership → ValidationError
        with pytest.raises(ValidationError):
            EmployeeService.create(hotel, admin_user, position="Receptionist")

    def test_create_employee_with_membership(self, hotel, admin_user, admin_membership):
        emp = EmployeeService.create(
            hotel, admin_user, position="Receptionist",
            department=Department.FRONT_DESK
        )
        assert emp.user == admin_user
        assert emp.department == Department.FRONT_DESK

    def test_employee_unique_per_hotel(self, hotel, admin_user, admin_membership):
        EmployeeService.create(hotel, admin_user, position="Receptionist", department=Department.FRONT_DESK)
        with pytest.raises(Exception):
            EmployeeService.create(hotel, admin_user, position="Manager", department=Department.FRONT_DESK)

    def test_get_employees_n1_safe(self, hotel, admin_user, admin_membership, django_assert_num_queries):
        EmployeeService.create(hotel, admin_user, department=Department.FRONT_DESK)
        with django_assert_num_queries(1):  # select_related("user") → single query
            emps = list(get_employees(hotel))
            for e in emps:
                _ = e.user.email


# ---------------------------------------------------------------------------
# BookingSource Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookingSource:
    def test_create_booking_source(self, hotel):
        src = BookingSourceService.create(hotel, "Booking.com", is_online=True, commission_rate=15)
        assert src.is_online is True
        assert src.commission_rate == Decimal("15")

    def test_booking_source_unique_per_hotel(self, hotel, booking_source):
        with pytest.raises(Exception):
            BookingSourceService.create(hotel, "Walk-in")

    def test_update_booking_source(self, hotel, booking_source):
        updated = BookingSourceService.update(booking_source, name="Walk-in Updated")
        assert updated.name == "Walk-in Updated"
