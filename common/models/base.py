"""
common/models/base.py
======================
المسار: common/models/base.py
الوظيفة: Abstract base models للمشروع كله. كل model في Hotel SaaS يرث من هنا.

الـ Models:
  ┌─────────────────────────────────────────────────────────┐
  │  UUIDModel       → id (UUID primary key)                │
  │  TimeStampedModel → created_at, updated_at              │
  │  ActiveModel     → is_active (soft filtering)           │
  │  HotelOwnedMixin → hotel FK (multi-tenancy scoping)     │
  │  BaseModel       → UUIDModel + TimeStampedModel + Active │
  │  SoftDeleteModel → deleted_at (soft delete pattern)     │
  └─────────────────────────────────────────────────────────┘

لماذا UUID وليس Integer IDs؟
  - في SaaS multi-tenant، UUIDs تمنع enumeration attacks
    (المستخدم لا يستطيع تخمين IDs من فنادق أخرى)
  - أسهل في الـ data migration بين environments
  - لا يوجد sequential prediction

مشكلة Django المعروفة مع db_index:
  - كل FK لـ hotel لازم db_index=True
  - Django يضيف index على FKs تلقائياً، لكن نؤكدها صراحةً هنا
  - نضيف composite indexes في كل model يحتاجها (مع الـ migration)

الاستخدام:
    from common.models import BaseModel, HotelOwnedMixin

    class Room(BaseModel, HotelOwnedMixin):
        room_number = models.CharField(max_length=10)
        # ...
        class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
            pass
"""

import uuid
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """
    Abstract model يستخدم UUID كـ primary key بدلاً من AutoField.

    لماذا؟
      - يمنع enumeration attacks في الـ API
      - يسمح بإنشاء IDs قبل حفظها في DB
      - مناسب للـ distributed systems

    Fields:
        id: UUID primary key (auto-generated, non-editable)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
        help_text="UUID unique identifier (auto-generated)",
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract model يضيف created_at و updated_at لكل record.

    ⚠️ db_index=True على created_at مهم جداً:
       - كل list endpoint بيُرتَّب بـ created_at افتراضياً
       - الـ index يجعل ORDER BY سريعاً على الجداول الكبيرة

    Fields:
        created_at: وقت الإنشاء (auto-set, indexed)
        updated_at: وقت آخر تعديل (auto-updated)
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Created At",
        help_text="Record creation timestamp (auto-set)",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Record last update timestamp (auto-updated)",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]  # الأحدث أولاً افتراضياً


class ActiveModel(models.Model):
    """
    Abstract model يضيف is_active flag للـ soft filtering.

    ⚠️ db_index=True على is_active مهم:
       - غالبية الـ queries تُفلتر بـ is_active=True
       - بدون index، full table scan في كل query

    ⚠️ هذا ليس soft delete — إخفاء المستخدم ≠ حذفه.
       لـ soft delete، استخدم SoftDeleteModel.

    Fields:
        is_active: هل الـ record نشط؟ (True افتراضياً، indexed)
    """

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether this record is active (soft-filter, not delete)",
    )

    class Meta:
        abstract = True


class HotelOwnedMixin(models.Model):
    """
    Mixin يضيف hotel FK لكل model مملوك لفندق معين.

    ⚠️ هذا هو جوهر الـ Multi-Tenancy:
       - كل model يرث من هنا محدود بفندق واحد
       - TenantManager يجبر على الـ scoping
       - db_index=True ضروري جداً (كل query تبدأ بـ hotel_id filter)

    ⚠️ related_name="%(class)ss":
       - يُولِّد related_name تلقائياً بناءً على اسم الـ class
       - Room → Hotel.rooms.all()
       - Customer → Hotel.customers.all()
       - يمنع تعارض الـ related_names

    Fields:
        hotel: FK لـ Hotel model (indexed, cascade delete)
    """

    hotel = models.ForeignKey(
        "tenants.Hotel",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,  # ضروري — كل query تبدأ بـ hotel_id
        verbose_name="Hotel",
        help_text="The hotel this record belongs to (multi-tenancy scope)",
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel, ActiveModel):
    """
    Base model جامع يرث من: UUIDModel + TimeStampedModel + ActiveModel.
    هذا هو الـ model الأساسي لمعظم الـ models في المشروع.

    الاستخدام:
        class Room(BaseModel, HotelOwnedMixin):
            ...
        class Hotel(BaseModel):  # Hotel نفسه لا يرث HotelOwnedMixin
            ...
    """

    class Meta(UUIDModel.Meta):
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteModel(models.Model):
    """
    Abstract model يضيف soft delete functionality.
    بدلاً من حذف الـ record، نضع deleted_at بتاريخ الحذف.

    ⚠️ استخدام محدود: للـ records التي لا يجوز حذفها نهائياً
       (مثلاً: FinancialTransaction, ReservationRoom)
       لا تُطبَّق على كل شيء.

    Fields:
        deleted_at: وقت الحذف الناعم (None = لم يُحذف)
    """

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Deleted At",
        help_text="Soft delete timestamp (null = active, not null = deleted)",
    )

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        """هل الـ record محذوف ناعمياً؟"""
        return self.deleted_at is not None

    def soft_delete(self):
        """حذف ناعم — يضع deleted_at بالوقت الحالي."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        """استعادة record محذوف ناعمياً."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])
