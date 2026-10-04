"""
rooms/services.py
=================
المسار: rooms/services.py
Phase: 4 — Master Data (+ Phase 7 mark_available update)

الـ Services هي Business Logic layer.
كل عملية تغيير في البيانات تمر هنا — الـ Serializers لا تحتوي منطق عمل.

مبدأ Service Layer:
  - Validation معقدة (cross-model rules)
  - Transactions عند الحاجة
  - لا database queries مباشرة في الـ views
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rooms.models import (
    Language, HotelLanguage, BookingSource,
    RoomType, RoomTypeTranslation, Room, RoomStatus
)


# ---------------------------------------------------------------------------
# Language Services
# ---------------------------------------------------------------------------

class LanguageService:
    """خدمات اللغات العالمية."""

    @staticmethod
    def create(code: str, name: str, native_name: str = "", is_rtl: bool = False) -> Language:
        """إنشاء لغة جديدة في النظام."""
        language = Language(
            code=code.lower(),
            name=name,
            native_name=native_name,
            is_rtl=is_rtl,
        )
        language.full_clean()
        language.save()
        return language


class HotelLanguageService:
    """خدمات لغات الفندق."""

    @staticmethod
    @transaction.atomic
    def add_language(hotel, language_code: str, is_default: bool = False) -> HotelLanguage:
        """
        إضافة لغة لفندق.
        إذا كانت is_default=True، تُلغى الـ default عن اللغات الأخرى.
        """
        try:
            language = Language.objects.get(code=language_code, is_active=True)
        except Language.DoesNotExist:
            raise ValidationError(_(f"Language '{language_code}' not found or inactive."))

        if is_default:
            # إلغاء الـ default عن اللغات الحالية
            HotelLanguage.objects.filter(hotel=hotel, is_default=True).update(is_default=False)

        hotel_lang, created = HotelLanguage.objects.get_or_create(
            hotel=hotel,
            language=language,
            defaults={"is_default": is_default},
        )
        if not created and is_default:
            hotel_lang.is_default = True
            hotel_lang.save()

        return hotel_lang


# ---------------------------------------------------------------------------
# BookingSource Services
# ---------------------------------------------------------------------------

class BookingSourceService:
    """خدمات مصادر الحجز."""

    @staticmethod
    def create(hotel, name: str, description: str = "", is_online: bool = False,
               commission_rate: float = 0) -> BookingSource:
        """إنشاء مصدر حجز جديد للفندق."""
        source = BookingSource(
            hotel=hotel,
            name=name,
            description=description,
            is_online=is_online,
            commission_rate=commission_rate,
        )
        source.full_clean()
        source.save()
        return source

    @staticmethod
    def update(source: BookingSource, **kwargs) -> BookingSource:
        """تحديث مصدر حجز."""
        for key, value in kwargs.items():
            setattr(source, key, value)
        source.full_clean()
        source.save()
        return source


# ---------------------------------------------------------------------------
# RoomType Services
# ---------------------------------------------------------------------------

class RoomTypeService:
    """خدمات أنواع الغرف."""

    @staticmethod
    @transaction.atomic
    def create(hotel, code: str, base_price, max_occupancy: int = 2,
               amenities: list = None, sort_order: int = 0,
               translations: list = None) -> RoomType:
        """
        إنشاء نوع غرفة مع ترجماته.

        Args:
            hotel: الفندق
            code: كود النوع
            base_price: السعر الأساسي
            max_occupancy: الحد الأقصى للأشخاص
            amenities: قائمة المميزات
            sort_order: ترتيب العرض
            translations: [{"language_code": "ar", "name": "...", "description": "..."}, ...]
        """
        room_type = RoomType(
            hotel=hotel,
            code=code.upper(),
            base_price=base_price,
            max_occupancy=max_occupancy,
            amenities=amenities or [],
            sort_order=sort_order,
        )
        room_type.full_clean()
        room_type.save()

        if translations:
            RoomTypeService._save_translations(room_type, translations)

        return room_type

    @staticmethod
    @transaction.atomic
    def update(room_type: RoomType, translations: list = None, **kwargs) -> RoomType:
        """تحديث نوع غرفة."""
        for key, value in kwargs.items():
            setattr(room_type, key, value)
        room_type.full_clean()
        room_type.save()

        if translations is not None:
            RoomTypeService._save_translations(room_type, translations)

        return room_type

    @staticmethod
    def _save_translations(room_type: RoomType, translations: list):
        """حفظ/تحديث ترجمات نوع الغرفة."""
        for trans_data in translations:
            lang_code = trans_data.get("language_code")
            try:
                language = Language.objects.get(code=lang_code)
            except Language.DoesNotExist:
                continue
            RoomTypeTranslation.objects.update_or_create(
                room_type=room_type,
                language=language,
                defaults={
                    "name": trans_data.get("name", ""),
                    "description": trans_data.get("description", ""),
                },
            )


# ---------------------------------------------------------------------------
# Room Services
# ---------------------------------------------------------------------------

class RoomService:
    """خدمات الغرف الفردية."""

    @staticmethod
    def create(hotel, room_type_id, room_number: str, floor: int = 1,
               status: str = RoomStatus.AVAILABLE, notes: str = "") -> Room:
        """إنشاء غرفة جديدة."""
        try:
            room_type = RoomType.objects.for_hotel(hotel).get(id=room_type_id)
        except RoomType.DoesNotExist:
            raise ValidationError(_(f"RoomType not found in this hotel."))

        room = Room(
            hotel=hotel,
            room_type=room_type,
            room_number=room_number,
            floor=floor,
            status=status,
            notes=notes,
        )
        room.full_clean()
        room.save()
        return room

    @staticmethod
    def update_status(room: Room, new_status: str, check_blocking: bool = True) -> Room:
        """
        تحديث حالة الغرفة.

        ⚠️ Phase 7 Rule: إذا كان check_blocking=True وفيه RoomIssue blocking مفتوح،
           لا يمكن تغيير الحالة إلى AVAILABLE.

        Args:
            room: الغرفة
            new_status: الحالة الجديدة
            check_blocking: هل نتحقق من RoomIssue blocking؟ (Phase 7)
        """
        if new_status == RoomStatus.AVAILABLE and check_blocking:
            # ⚠️ Phase 7: سيتم استكمال هذا الـ check في Phase 7
            # بـ annotate(Exists(RoomIssue.filter(blocking=True, status__in=[...])))
            # الآن: placeholder يُشار إليه ونُكمله في Phase 7
            RoomService._check_no_blocking_issues(room)

        room.status = new_status
        room.save(update_fields=["status", "updated_at"])
        return room

    @staticmethod
    def _check_no_blocking_issues(room: Room):
        """
        Phase 7: يتحقق من عدم وجود RoomIssue blocking مفتوح.
        يُطلَق قبل تغيير Room.status إلى AVAILABLE.

        ⚠️ N+1 Safe: query مباشرة .exists() بدل load كل الـ issues.
        """
        from maintenance.models import RoomIssue, IssueStatus
        has_blocking = RoomIssue.objects.filter(
            room=room,
            blocking=True,
            status__in=[IssueStatus.OPEN, IssueStatus.IN_PROGRESS],
        ).exists()
        if has_blocking:
            raise ValidationError(_(
                f"Room {room.room_number} cannot be marked as AVAILABLE "
                f"while it has open blocking maintenance issues."
            ))

    @staticmethod
    def update(room: Room, **kwargs) -> Room:
        """تحديث بيانات غرفة."""
        allowed_fields = {"floor", "notes", "room_number"}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(room, key, value)
        room.full_clean()
        room.save()
        return room
