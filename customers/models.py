"""
customers/models.py
===================
المسار: customers/models.py
Phase: 4 — Master Data

Models:
  ┌──────────────────────────────────────────────────────────────┐
  │  Customer  → guest/client profile per hotel                  │
  │  Employee  → hotel staff member linked to User               │
  └──────────────────────────────────────────────────────────────┘

مشاكل Django المحلولة:
  1. Search على Customer — index على phone + email، استخدم SearchVector بدل icontains
  2. Employee مرتبط بـ User بـ FK (OneToOne per hotel ليس globally unique)
  3. N+1 في Employee list → select_related("user") في Selector
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin
from common.models.managers import TenantManager


# ---------------------------------------------------------------------------
# Customer — guest profile
# ---------------------------------------------------------------------------

class IDType(models.TextChoices):
    """نوع وثيقة الهوية."""
    PASSPORT = "passport", _("Passport")
    NATIONAL_ID = "national_id", _("National ID")
    DRIVING_LICENSE = "driving_license", _("Driving License")
    OTHER = "other", _("Other")


class Customer(BaseModel, HotelOwnedMixin):
    """
    ملف تعريف الضيف داخل فندق معين.

    ⚠️ Email و Phone لا يشترطان التفرد العالمي — نفس العميل قد يكون
       في أكثر من فندق بسجلات منفصلة (multi-tenant).

    ⚠️ Index على phone و email — Search queries الأكثر شيوعاً هي بالهاتف أو البريد.

    ⚠️ Full-text search: استخدم SearchVector في Selector بدل icontains مباشرةً
       (icontains بطيء على جداول كبيرة بدون index مناسب).

    Fields:
        hotel: FK للفندق
        first_name, last_name: الاسم
        email: البريد الإلكتروني
        phone: رقم الهاتف (indexed)
        nationality: الجنسية
        id_type: نوع وثيقة الهوية
        id_number: رقم وثيقة الهوية
        date_of_birth: تاريخ الميلاد
        notes: ملاحظات داخلية
        vip_status: هل العميل VIP؟
    """

    objects = TenantManager()

    first_name = models.CharField(
        max_length=100,
        verbose_name=_("First Name"),
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name=_("Last Name"),
    )
    email = models.EmailField(
        blank=True,
        db_index=True,   # ← indexed for search
        verbose_name=_("Email"),
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,   # ← indexed for search (most common lookup)
        verbose_name=_("Phone"),
    )
    nationality = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Nationality"),
        help_text="Country name or ISO 3166-1 alpha-2 code",
    )
    id_type = models.CharField(
        max_length=30,
        choices=IDType.choices,
        blank=True,
        verbose_name=_("ID Type"),
    )
    id_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("ID Number"),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date of Birth"),
    )
    vip_status = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("VIP Status"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text="Internal notes about this guest",
    )
    # Track how many stays (denormalized counter updated by service layer)
    total_stays = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Stays"),
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        indexes = [
            # Composite index for hotel-scoped phone search
            models.Index(fields=["hotel", "phone"], name="idx_customer_hotel_phone"),
            models.Index(fields=["hotel", "email"], name="idx_customer_hotel_email"),
            models.Index(fields=["hotel", "last_name"], name="idx_customer_hotel_name"),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone or self.email})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# ---------------------------------------------------------------------------
# Employee — hotel staff member
# ---------------------------------------------------------------------------

class Department(models.TextChoices):
    """الأقسام الوظيفية في الفندق."""
    FRONT_DESK = "front_desk", _("Front Desk")
    HOUSEKEEPING = "housekeeping", _("Housekeeping")
    MAINTENANCE = "maintenance", _("Maintenance")
    FOOD_BEVERAGE = "food_beverage", _("Food & Beverage")
    MANAGEMENT = "management", _("Management")
    SECURITY = "security", _("Security")
    OTHER = "other", _("Other")


class Employee(BaseModel, HotelOwnedMixin):
    """
    موظف في الفندق مرتبط بحساب User.

    ⚠️ user + hotel ليسا globally unique بالضرورة في حالة نظام multi-tenant
       لكن نضع UniqueConstraint(user, hotel) لمنع تكرار نفس الموظف في فندق.

    ⚠️ N+1 في Employee list → select_related("user") في Selector.

    Fields:
        hotel: FK للفندق
        user: FK لـ User (حساب النظام)
        employee_id: رقم موظف داخلي (فريد داخل الفندق)
        position: المنصب الوظيفي
        department: القسم
        hire_date: تاريخ التعيين
        is_active: هل الموظف نشط؟ (من BaseModel/ActiveModel)
    """

    objects = TenantManager()

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="employee_profiles",
        db_index=True,
        verbose_name=_("User Account"),
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Employee ID"),
        help_text="Internal employee number (unique per hotel)",
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Position"),
        help_text="Job title (e.g., Receptionist, Housekeeper)",
    )
    department = models.CharField(
        max_length=30,
        choices=Department.choices,
        default=Department.FRONT_DESK,
        db_index=True,
        verbose_name=_("Department"),
    )
    hire_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Hire Date"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
    )

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        constraints = [
            # موظف لا يمكنه الظهور مرتين في نفس الفندق
            models.UniqueConstraint(
                fields=["hotel", "user"],
                name="unique_employee_per_hotel",
            )
        ]
        indexes = [
            models.Index(
                fields=["hotel", "department"],
                name="idx_employee_hotel_department",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.full_name} [{self.department}] @ {self.hotel.name}"

    @property
    def full_name(self) -> str:
        return self.user.full_name
