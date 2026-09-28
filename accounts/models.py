"""
accounts/models.py
==================
المسار: accounts/models.py
الوظيفة: Custom User model + RBAC models (HotelMembership, Role, Permission, RolePermission).

⚠️ مهم جداً في Django:
  AUTH_USER_MODEL = "accounts.User" يجب أن يُحدَّد في settings قبل أي migration.
  إذا تم تغييره بعد ذلك، ستحدث مشاكل معقدة في migrations.
  لهذا عرَّفناه من Phase 0.

Models:
  ┌─────────────────────────────────────────────────────────────┐
  │  User            → Custom User يرث AbstractUser             │
  │  HotelMembership → ربط User بـ Hotel بـ role                │
  │  Role            → دور داخل فندق (مثلاً: Manager, Staff)   │
  │  Permission      → صلاحية محددة (مثلاً: rooms.manage)       │
  │  RolePermission  → ربط Role بـ Permission                   │
  └─────────────────────────────────────────────────────────────┘

مشاكل Django المحلولة:
  1. N+1 في Permission check: prefetch_related على role__rolepermission_set__permission
  2. Permission Caching: في common/permissions (يُفعَّل بعد هذا الملف)
  3. Multiple Memberships: مستخدم واحد يمكنه الانتماء لأكثر من فندق

الـ Permissions Schema:
  "rooms.view"       → عرض الغرف
  "rooms.manage"     → إدارة الغرف (إنشاء/تعديل/حذف)
  "finance.view"     → عرض المعاملات المالية
  "finance.manage"   → إدارة المعاملات المالية
  "reservations.view" → عرض الحجوزات
  "reservations.manage" → إدارة الحجوزات
  ... إلخ
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, UUIDModel, TimeStampedModel
from common.models.managers import TenantManager


class User(AbstractUser, UUIDModel, TimeStampedModel):
    """
    Custom User Model يرث من AbstractUser.

    ⚠️ نستخدم email كـ login identifier بدلاً من username.
    username لا يزال موجوداً (من AbstractUser) لكنه اختياري.

    ⚠️ يرث من UUIDModel و TimeStampedModel لكن ليس من BaseModel الكامل
       لأن AbstractUser لديه id خاص به ونحتاج نتجاوزه.

    Fields (إضافة على AbstractUser):
        phone: رقم الهاتف (اختياري)
        avatar: صورة المستخدم
        is_platform_admin: هل هو admin على مستوى المنصة كلها؟
        preferred_language: اللغة المفضلة

    الـ login عبر email:
        USERNAME_FIELD = "email"
        REQUIRED_FIELDS = ["username"] (مطلوب لـ AbstractUser)
    """

    # Override email ليكون unique (AbstractUser لا يجعله unique افتراضياً)
    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        help_text="Used as the primary login identifier",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone"),
        help_text="User phone number (optional)",
    )
    avatar = models.ImageField(
        upload_to="users/avatars/",
        null=True,
        blank=True,
        verbose_name=_("Avatar"),
    )
    is_platform_admin = models.BooleanField(
        default=False,
        verbose_name=_("Is Platform Admin"),
        help_text="Platform-level admin (not hotel-specific). Can manage all hotels.",
    )
    preferred_language = models.CharField(
        max_length=10,
        default="en",
        verbose_name=_("Preferred Language"),
        help_text="ISO 639-1 language code",
    )

    # استخدام email كـ login field
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta(UUIDModel.Meta):
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def full_name(self) -> str:
        """الاسم الكامل أو email كـ fallback."""
        return self.get_full_name() or self.email


class MembershipStatus(models.TextChoices):
    """حالات العضوية في الفندق."""
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    SUSPENDED = "suspended", _("Suspended")
    INVITED = "invited", _("Invited (pending acceptance)")


class HotelMembership(BaseModel):
    """
    ربط المستخدم بالفندق مع دور محدد.

    مستخدم واحد يمكنه الانتماء لأكثر من فندق بأدوار مختلفة.
    مثلاً: المستخدم X → Manager في فندق A، Staff في فندق B.

    Fields:
        user: المستخدم
        hotel: الفندق
        role: الدور (FK لـ Role)
        status: حالة العضوية
        joined_at: تاريخ الانضمام

    Constraints:
        unique_together: (user, hotel) — مستخدم لا يمكنه أن يكون عضواً مرتين في نفس الفندق

    ⚠️ N+1 المحتمل:
        عند عرض قائمة الأعضاء مع role.permissions، نستخدم:
        HotelMembership.objects.select_related("user", "role")
                               .prefetch_related("role__rolepermissions__permission")
    """

    # TenantManager يُضيف .for_hotel() method للـ queryset
    objects = TenantManager()

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
        verbose_name=_("User"),
    )
    hotel = models.ForeignKey(
        "tenants.Hotel",
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
        verbose_name=_("Hotel"),
    )
    role = models.ForeignKey(
        "Role",
        on_delete=models.PROTECT,  # PROTECT: لا يمكن حذف Role لو فيه أعضاء
        related_name="memberships",
        null=True,
        blank=True,
        verbose_name=_("Role"),
        help_text="User's role in this hotel",
    )
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Joined At"),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Hotel Membership")
        verbose_name_plural = _("Hotel Memberships")
        constraints = [
            # مستخدم لا يمكنه الانضمام لنفس الفندق مرتين
            models.UniqueConstraint(
                fields=["user", "hotel"],
                name="unique_user_hotel_membership",
            )
        ]
        indexes = [
            # Composite index للـ query: "أعضاء فندق معين النشطين"
            models.Index(fields=["hotel", "status"], name="idx_membership_hotel_status"),
            # Composite index للـ query: "فنادق مستخدم معين"
            models.Index(fields=["user", "status"], name="idx_membership_user_status"),
        ]

    def __str__(self) -> str:
        role_name = self.role.name if self.role else "No Role"
        return f"{self.user.email} @ {self.hotel.name} ({role_name})"


class Role(BaseModel):
    """
    دور داخل فندق محدد (مثلاً: Manager, Receptionist, Housekeeping).
    الأدوار مخصصة لكل فندق — لا توجد أدوار عالمية مشتركة.

    Fields:
        hotel: الفندق (FK)
        name: اسم الدور
        description: وصف الدور
        is_system_role: هل هو دور نظام لا يمكن حذفه؟

    ⚠️ لا يرث HotelOwnedMixin لأن hotel FK هنا ليس له TenantManager
       (Role يحتاج أحياناً إلى query بدون hotel context في الـ admin)
    """

    hotel = models.ForeignKey(
        "tenants.Hotel",
        on_delete=models.CASCADE,
        related_name="roles",
        db_index=True,
        verbose_name=_("Hotel"),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Role Name"),
        help_text="e.g., Manager, Receptionist, Housekeeping Staff",
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
    )
    is_system_role = models.BooleanField(
        default=False,
        verbose_name=_("Is System Role"),
        help_text="System roles cannot be deleted (e.g., Owner, Manager)",
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        constraints = [
            # اسم الدور فريد داخل الفندق
            models.UniqueConstraint(
                fields=["hotel", "name"],
                name="unique_role_name_per_hotel",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} @ {self.hotel.name}"

    def get_permission_codes(self) -> list[str]:
        """
        يُرجع قائمة أكواد الصلاحيات لهذا الدور.

        ⚠️ N+1 تحذير:
            هذه الـ method تفترض أن rolepermissions و permission مُجلَبَة مسبقاً.
            استخدم prefetch_related("rolepermissions__permission") عند استدعائها.

        Returns:
            List of permission codes (e.g., ["rooms.view", "rooms.manage"])
        """
        return [rp.permission.code for rp in self.rolepermissions.all()]


class Permission(models.Model):
    """
    صلاحية محددة في النظام.
    الصلاحيات عالمية (مش per-hotel) — فندق يُعيِّن Roles بصلاحيات معروفة.

    Format: "module.action"
    Examples:
        rooms.view       → عرض الغرف
        rooms.manage     → إدارة الغرف
        finance.view     → عرض المالية
        finance.manage   → إدارة المالية
        reservations.view → عرض الحجوزات
        reports.view     → عرض التقارير

    ⚠️ لا يرث BaseModel لأن الصلاحيات ثابتة ونادراً ما تتغير
       ولا تحتاج UUID أو timestamps (Integer PK أسرع للـ lookups الكثيرة).
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Permission Code"),
        help_text="Format: 'module.action' (e.g., 'rooms.manage')",
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Permission Name"),
        help_text="Human-readable name (e.g., 'Manage Rooms')",
    )
    module = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Module"),
        help_text="The module this permission belongs to (e.g., 'rooms', 'finance')",
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
    )

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ["module", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class RolePermission(models.Model):
    """
    جدول الربط بين Role و Permission.
    يُحدِّد أي صلاحيات يملكها كل دور.

    ⚠️ N+1 المحتمل الأهم في Phase 3:
        عند التحقق من صلاحيات مستخدم:
        HotelMembership.objects
            .select_related("role")
            .prefetch_related("role__rolepermissions__permission")
        
        هذا يجلب كل شيء في 3 queries فقط بدل N+1 queries.

    ⚠️ Caching:
        نتيجة get_permission_codes() تُخزَّن في cache بـ key:
        "perms:{user_id}:{hotel_id}" → تتحدث عند تغيير Role/RolePermission
    """

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="rolepermissions",
        db_index=True,
        verbose_name=_("Role"),
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="rolepermissions",
        db_index=True,
        verbose_name=_("Permission"),
    )

    class Meta:
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        constraints = [
            # لا تكرار للربط بين نفس الـ Role والـ Permission
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            )
        ]
        indexes = [
            # Index للـ query: "كل صلاحيات دور معين"
            models.Index(fields=["role", "permission"], name="idx_rolepermission_role"),
        ]

    def __str__(self) -> str:
        return f"{self.role.name} → {self.permission.code}"
