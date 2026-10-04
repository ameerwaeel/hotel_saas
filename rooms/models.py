"""
rooms/models.py
===============
المسار: rooms/models.py
Phase: 4 — Master Data

Models:
  ┌──────────────────────────────────────────────────────────────┐
  │  Language            → global language registry              │
  │  HotelLanguage       → per-hotel language config             │
  │  BookingSource       → per-hotel booking channels            │
  │  RoomType            → category of rooms (with i18n)         │
  │  RoomTypeTranslation → i18n name/description per language    │
  │  Room                → individual room in a hotel            │
  └──────────────────────────────────────────────────────────────┘

مشاكل Django المحلولة:
  1. N+1 في RoomType list → prefetch_related("translations") في Selector
  2. N+1 في Room list → select_related("room_type") في Selector
  3. room_number unique per hotel → UniqueConstraint(["hotel","room_number"])
  4. Availability queries → db_index على Room.status
  5. Translation uniqueness → unique_together (room_type, language)
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin
from common.models.managers import TenantManager


# ---------------------------------------------------------------------------
# Language — global registry (no hotel FK)
# ---------------------------------------------------------------------------

class Language(models.Model):
    """
    سجل عالمي للغات المدعومة في النظام.
    لا يرث HotelOwnedMixin — اللغات عالمية مشتركة بين جميع الفنادق.

    Fields:
        code: ISO 639-1 language code (e.g., "en", "ar", "fr")
        name: اسم اللغة بالإنجليزية (e.g., "English", "Arabic")
        native_name: اسم اللغة بلغتها الأصلية (e.g., "العربية")
        is_rtl: هل هي لغة RTL (من اليمين لليسار)؟
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name=_("Language Code"),
        help_text="ISO 639-1 code (e.g., 'en', 'ar', 'fr')",
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Language Name"),
        help_text="English name of the language",
    )
    native_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Native Name"),
        help_text="Name in the language itself (e.g., العربية)",
    )
    is_rtl = models.BooleanField(
        default=False,
        verbose_name=_("Is RTL"),
        help_text="Right-to-left language direction?",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
    )

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


# ---------------------------------------------------------------------------
# HotelLanguage — per-hotel language config
# ---------------------------------------------------------------------------

class HotelLanguage(BaseModel, HotelOwnedMixin):
    """
    تحديد اللغات المدعومة داخل فندق معين، مع تحديد اللغة الافتراضية.

    ⚠️ UniqueConstraint(hotel, language) — فندق لا يسجّل نفس اللغة مرتين.
    ⚠️ فندق يجب أن يكون لديه لغة افتراضية واحدة فقط (يتحقق منه Service Layer).

    Fields:
        hotel: FK للفندق
        language: FK للغة
        is_default: هل هي اللغة الافتراضية للفندق؟
    """

    objects = TenantManager()

    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        related_name="hotel_languages",
        verbose_name=_("Language"),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Is Default"),
        help_text="Default language for this hotel",
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Hotel Language")
        verbose_name_plural = _("Hotel Languages")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "language"],
                name="unique_hotel_language",
            )
        ]

    def __str__(self) -> str:
        default_tag = " [Default]" if self.is_default else ""
        return f"{self.hotel.name} — {self.language.name}{default_tag}"


# ---------------------------------------------------------------------------
# BookingSource — per-hotel booking channels
# ---------------------------------------------------------------------------

class BookingSource(BaseModel, HotelOwnedMixin):
    """
    مصادر الحجوزات (مثلاً: Walk-in, Booking.com, Expedia, Phone).
    مخصصة لكل فندق — كل فندق يحدد مصادره الخاصة.

    Fields:
        hotel: FK للفندق
        name: اسم المصدر
        description: وصف اختياري
        is_online: هل هو مصدر إلكتروني (OTA)؟
        commission_rate: نسبة العمولة (إن وجدت)
    """

    objects = TenantManager()

    name = models.CharField(
        max_length=100,
        verbose_name=_("Source Name"),
        help_text="e.g., Walk-in, Booking.com, Phone",
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
    )
    is_online = models.BooleanField(
        default=False,
        verbose_name=_("Is Online"),
        help_text="Online travel agency (OTA) or direct booking?",
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Commission Rate (%)"),
        help_text="Commission percentage (if applicable)",
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Booking Source")
        verbose_name_plural = _("Booking Sources")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "name"],
                name="unique_booking_source_per_hotel",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} @ {self.hotel.name}"


# ---------------------------------------------------------------------------
# RoomType — category of rooms with i18n support
# ---------------------------------------------------------------------------

class RoomType(BaseModel, HotelOwnedMixin):
    """
    نوع الغرفة (مثلاً: Standard, Deluxe, Suite).
    يدعم الترجمات عبر RoomTypeTranslation.

    ⚠️ N+1 تحذير:
       عند عرض قائمة أنواع الغرف مع الترجمات، استخدم:
       RoomType.objects.for_hotel(hotel).prefetch_related("translations")
       
    ⚠️ code فريد داخل الفندق (UniqueConstraint).

    Fields:
        hotel: FK للفندق
        code: كود مختصر للنوع (e.g., "STD", "DLX", "STE")
        base_price: السعر الأساسي لليلة
        max_occupancy: الحد الأقصى لعدد الأشخاص
        amenities: قائمة المميزات (JSON)
        sort_order: ترتيب العرض
    """

    objects = TenantManager()

    code = models.CharField(
        max_length=20,
        verbose_name=_("Room Type Code"),
        help_text="Short code (e.g., STD, DLX, STE)",
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Base Price per Night"),
        help_text="Default nightly rate (DecimalField — never FloatField for money)",
    )
    max_occupancy = models.PositiveSmallIntegerField(
        default=2,
        verbose_name=_("Max Occupancy"),
    )
    amenities = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Amenities"),
        help_text="List of amenity strings (e.g., ['WiFi', 'AC', 'Mini-bar'])",
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        verbose_name=_("Sort Order"),
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Room Type")
        verbose_name_plural = _("Room Types")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "code"],
                name="unique_room_type_code_per_hotel",
            )
        ]
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return f"{self.code} @ {self.hotel.name}"

    def get_name(self, language_code: str = "en") -> str:
        """إرجاع اسم نوع الغرفة بالغة المطلوبة (fallback للـ code)."""
        try:
            return self.translations.get(language__code=language_code).name
        except RoomTypeTranslation.DoesNotExist:
            return self.code


# ---------------------------------------------------------------------------
# RoomTypeTranslation — i18n translations for RoomType
# ---------------------------------------------------------------------------

class RoomTypeTranslation(models.Model):
    """
    ترجمات اسم ووصف نوع الغرفة لكل لغة.

    ⚠️ unique_together (room_type, language) — لا تكرار للغة لنفس النوع.
    ⚠️ لا يرث BaseModel — لا يحتاج UUID أو is_active (بيانات مساعدة).

    Fields:
        room_type: FK لـ RoomType
        language: FK لـ Language
        name: الاسم باللغة المحددة
        description: الوصف باللغة المحددة
    """

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Room Type"),
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        related_name="room_type_translations",
        verbose_name=_("Language"),
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Name"),
        help_text="Room type name in this language",
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
    )

    class Meta:
        verbose_name = _("Room Type Translation")
        verbose_name_plural = _("Room Type Translations")
        constraints = [
            models.UniqueConstraint(
                fields=["room_type", "language"],
                name="unique_room_type_translation",
            )
        ]

    def __str__(self) -> str:
        return f"{self.room_type.code} [{self.language.code}]: {self.name}"


# ---------------------------------------------------------------------------
# Room — individual room in a hotel
# ---------------------------------------------------------------------------

class RoomStatus(models.TextChoices):
    """حالات الغرفة."""
    AVAILABLE = "available", _("Available")
    OCCUPIED = "occupied", _("Occupied")
    MAINTENANCE = "maintenance", _("Under Maintenance")
    CLEANING = "cleaning", _("Being Cleaned")
    INSPECTING = "inspecting", _("Being Inspected")
    OUT_OF_ORDER = "out_of_order", _("Out of Order")


class Room(BaseModel, HotelOwnedMixin):
    """
    غرفة فندقية محددة (وحدة الحجز الأساسية).

    ⚠️ room_number فريد داخل الفندق فقط (UniqueConstraint per hotel):
       فندق A يمكنه أن يكون لديه غرفة 101، وفندق B أيضاً.

    ⚠️ Index على status — قائمة الغرف المتاحة تُحسب بتكرار شديد في Availability.

    ⚠️ N+1 تحذير في Room list:
       استخدم select_related("room_type") دائماً في الـ Selector.

    Fields:
        hotel: FK للفندق
        room_type: FK لـ RoomType (select_related في queries)
        room_number: رقم الغرفة (فريد داخل الفندق)
        floor: الطابق
        status: حالة الغرفة (indexed)
        notes: ملاحظات داخلية
    """

    objects = TenantManager()

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,  # PROTECT: لا نحذف RoomType لو فيه غرف
        related_name="rooms",
        db_index=True,
        verbose_name=_("Room Type"),
    )
    room_number = models.CharField(
        max_length=20,
        verbose_name=_("Room Number"),
        help_text="Unique within the hotel (e.g., '101', '201A')",
    )
    floor = models.SmallIntegerField(
        default=1,
        verbose_name=_("Floor"),
    )
    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.AVAILABLE,
        db_index=True,   # ← critical for Availability queries
        verbose_name=_("Status"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text="Internal notes about this room",
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
        constraints = [
            # ⚠️ room_number unique per hotel (not globally unique)
            models.UniqueConstraint(
                fields=["hotel", "room_number"],
                name="unique_room_number_per_hotel",
            )
        ]
        indexes = [
            # Composite index: Availability query = hotel + status + room_type
            models.Index(
                fields=["hotel", "status"],
                name="idx_room_hotel_status",
            ),
            models.Index(
                fields=["hotel", "room_type", "status"],
                name="idx_room_hotel_type_status",
            ),
        ]

    def __str__(self) -> str:
        return f"Room {self.room_number} ({self.room_type.code}) @ {self.hotel.name}"
