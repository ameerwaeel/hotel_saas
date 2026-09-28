"""
tenants/models.py
==================
المسار: tenants/models.py
الوظيفة: النماذج الأساسية للـ Multi-Tenancy — Hotel هو جذر كل شيء.

Models:
  ┌──────────────────────────────────────────────┐
  │  Hotel         → الفندق (Tenant الأساسي)     │
  │  HotelSettings → إعدادات الفندق (OneToOne)   │
  └──────────────────────────────────────────────┘

مشاكل Django التي تم حلها هنا:
  1. **Composite Index**: index على (slug) لأنه يُستخدم في الـ URL routing
  2. **Unique Subdomain**: subdomain unique عالمياً (مش per-hotel)
  3. **Status Field**: استخدام TextChoices بدل string literals
  4. **OneToOneField على HotelSettings**: يضمن إعداد واحد لكل فندق

الـ Hotel لا يرث HotelOwnedMixin لأنه هو نفسه الـ tenant root.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel


class HotelStatus(models.TextChoices):
    """
    حالات الفندق المتاحة.
    نستخدم TextChoices بدل string literals لمنع أخطاء الكتابة.
    """
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    SUSPENDED = "suspended", _("Suspended")
    TRIAL = "trial", _("Trial")


class Hotel(BaseModel):
    """
    النموذج الأساسي للفندق (Tenant).
    كل model آخر في النظام يرتبط بـ Hotel عبر HotelOwnedMixin.

    Fields:
        name: اسم الفندق
        slug: معرف URL-friendly (unique)
        subdomain: الـ subdomain للفندق (hotel.saas.com)
        email: البريد الإلكتروني الرسمي
        phone: رقم الهاتف
        address: العنوان
        city: المدينة
        country: الدولة (ISO 3166-1 alpha-2)
        timezone: timezone الفندق (مثل "Africa/Cairo")
        default_currency: العملة الافتراضية (ISO 4217)
        default_language: اللغة الافتراضية (ISO 639-1)
        status: حالة الفندق (active/inactive/suspended/trial)
        logo: صورة الشعار

    Indexes:
        - slug: للـ URL routing السريع
        - subdomain: للـ tenant resolution من الـ domain
        - status: للفلترة السريعة
        - (status, is_active): composite للـ active hotels query

    Meta:
        verbose_name: "Hotel"
        ordering: ["name"]
    """

    name = models.CharField(
        max_length=255,
        verbose_name=_("Hotel Name"),
        help_text="Full name of the hotel",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Slug"),
        help_text="URL-friendly identifier (auto-generated from name)",
    )
    subdomain = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Subdomain"),
        help_text="Subdomain for tenant routing (e.g., 'hilton' → hilton.saas.com)",
    )
    email = models.EmailField(
        verbose_name=_("Email"),
        help_text="Official hotel contact email",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone"),
        help_text="Hotel phone number",
    )
    address = models.TextField(
        blank=True,
        verbose_name=_("Address"),
        help_text="Full postal address",
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("City"),
    )
    country = models.CharField(
        max_length=2,
        blank=True,
        verbose_name=_("Country"),
        help_text="ISO 3166-1 alpha-2 country code (e.g., EG, US)",
    )
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        verbose_name=_("Timezone"),
        help_text="Hotel local timezone (e.g., Africa/Cairo)",
    )
    default_currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name=_("Default Currency"),
        help_text="ISO 4217 currency code (e.g., USD, EGP)",
    )
    default_language = models.CharField(
        max_length=10,
        default="en",
        verbose_name=_("Default Language"),
        help_text="ISO 639-1 language code (e.g., en, ar)",
    )
    status = models.CharField(
        max_length=20,
        choices=HotelStatus.choices,
        default=HotelStatus.TRIAL,
        db_index=True,
        verbose_name=_("Status"),
        help_text="Current hotel status (active/inactive/suspended/trial)",
    )
    logo = models.ImageField(
        upload_to="hotels/logos/",
        null=True,
        blank=True,
        verbose_name=_("Logo"),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Hotel")
        verbose_name_plural = _("Hotels")
        ordering = ["name"]
        indexes = [
            # Composite index للـ active hotels query (أكثر query شيوعاً)
            models.Index(fields=["status", "is_active"], name="idx_hotel_status_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.subdomain})"

    @property
    def is_operational(self) -> bool:
        """هل الفندق يعمل ويمكن إجراء reservations؟"""
        return self.is_active and self.status in [HotelStatus.ACTIVE, HotelStatus.TRIAL]


class HotelSettings(BaseModel):
    """
    إعدادات الفندق التشغيلية (OneToOne مع Hotel).
    يُنشأ تلقائياً عند إنشاء Hotel عبر Django signal.

    Fields:
        hotel: One-to-one relation مع Hotel
        checkin_time: وقت الـ check-in الافتراضي
        checkout_time: وقت الـ check-out الافتراضي
        exchange_rate_mode: طريقة إدارة أسعار الصرف
        allow_overbooking: السماح بـ overbooking
        max_advance_booking_days: الحد الأقصى للحجز المسبق
        auto_close_daily: إغلاق اليوم المالي تلقائياً
        invoice_prefix: بادئة رقم الفاتورة

    Note:
        HotelSettings لا يرث HotelOwnedMixin لأنه يرتبط بـ hotel عبر OneToOneField
        وليس ForeignKey عادي.
    """

    class ExchangeRateMode(models.TextChoices):
        MANUAL = "manual", _("Manual (staff updates rates)")
        AUTO = "auto", _("Auto (fetch from API)")
        FIXED = "fixed", _("Fixed (no conversion)")

    hotel = models.OneToOneField(
        Hotel,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name=_("Hotel"),
        help_text="The hotel these settings belong to",
    )
    checkin_time = models.TimeField(
        default="14:00",
        verbose_name=_("Check-in Time"),
        help_text="Default check-in time (e.g., 14:00)",
    )
    checkout_time = models.TimeField(
        default="12:00",
        verbose_name=_("Check-out Time"),
        help_text="Default check-out time (e.g., 12:00)",
    )
    exchange_rate_mode = models.CharField(
        max_length=10,
        choices=ExchangeRateMode.choices,
        default=ExchangeRateMode.MANUAL,
        verbose_name=_("Exchange Rate Mode"),
    )
    allow_overbooking = models.BooleanField(
        default=False,
        verbose_name=_("Allow Overbooking"),
        help_text="Allow booking a room that might be occupied",
    )
    max_advance_booking_days = models.PositiveIntegerField(
        default=365,
        verbose_name=_("Max Advance Booking Days"),
        help_text="Maximum days in advance a reservation can be made",
    )
    auto_close_daily = models.BooleanField(
        default=True,
        verbose_name=_("Auto Close Daily"),
        help_text="Automatically close the daily financial period at midnight",
    )
    invoice_prefix = models.CharField(
        max_length=10,
        default="INV",
        verbose_name=_("Invoice Prefix"),
        help_text="Prefix for invoice numbers (e.g., INV → INV-0001)",
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Hotel Settings")
        verbose_name_plural = _("Hotel Settings")

    def __str__(self) -> str:
        return f"Settings for {self.hotel.name}"
