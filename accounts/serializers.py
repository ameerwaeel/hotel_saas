"""
accounts/serializers.py
=========================
المسار: accounts/serializers.py
الوظيفة: Serializers للـ Authentication و RBAC.

Serializers:
  ┌────────────────────────────────────────────────────────────────┐
  │  UserSerializer            → عرض بيانات المستخدم              │
  │  LoginSerializer           → تسجيل الدخول (email + password)   │
  │  PasswordChangeSerializer  → تغيير كلمة المرور                 │
  │  PasswordResetSerializer   → طلب reset كلمة المرور             │
  │  PermissionSerializer      → عرض صلاحية واحدة                  │
  │  RoleSerializer            → عرض دور مع صلاحياته               │
  │  HotelMembershipSerializer → عرض عضوية مع الـ role والصلاحيات  │
  └────────────────────────────────────────────────────────────────┘

مشاكل Django المحلولة:
  1. **N+1 في HotelMembershipSerializer:**
     يعرض role و permissions كـ nested objects.
     بدون prefetch: N+1 queries.
     الحل: prefetch_related("role__rolepermissions__permission") في الـ view.

  2. **Validation في الـ Serializer vs Service:**
     الـ serializers تتحقق من الشكل فقط (types, required, format).
     الـ business logic (هل الـ user له membership) تكون في الـ Service.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from .models import User, HotelMembership, Role, Permission, RolePermission


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer لعرض بيانات المستخدم.
    لا يُظهر password أو حقول حساسة.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "preferred_language",
            "is_platform_admin",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "is_platform_admin"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer لتعديل بيانات المستخدم (محدود الحقول).
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar", "preferred_language"]


class LoginSerializer(serializers.Serializer):
    """
    Serializer لتسجيل الدخول.
    يتحقق من email و password ويُرجع User instance.

    ⚠️ التحقق من credentials هنا لأنه شكل البيانات.
       أما الـ JWT token generation، فيكون في الـ view.
    """

    email = serializers.EmailField(
        help_text="User email address",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="User password",
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise ValidationError("Both email and password are required.")

        # Django authenticate
        user = authenticate(
            request=self.context.get("request"),
            username=email,  # USERNAME_FIELD = email
            password=password,
        )

        if not user:
            raise AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        attrs["user"] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer لتغيير كلمة المرور.
    يتحقق من كلمة المرور القديمة ويطبق الـ validators على الجديدة.
    """

    old_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer لطلب إعادة تعيين كلمة المرور."""

    email = serializers.EmailField()

    def validate_email(self, value):
        # لا نُخبر المستخدم إذا كان الـ email موجوداً أم لا (security)
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer لتأكيد إعادة تعيين كلمة المرور باستخدام الـ token."""

    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["new_password"])
        return attrs


# ---------------------------------------------------------------------------
# RBAC Serializers
# ---------------------------------------------------------------------------

class PermissionSerializer(serializers.ModelSerializer):
    """Serializer لعرض صلاحية واحدة."""

    class Meta:
        model = Permission
        fields = ["id", "code", "name", "module", "description"]
        read_only_fields = ["id"]


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer لعرض دور مع صلاحياته.

    ⚠️ N+1 تحذير:
        permissions = PermissionSerializer(many=True, source="...")
        يتطلب prefetch_related("rolepermissions__permission") في الـ view.

    الـ View يجب أن يستخدم:
        Role.objects.prefetch_related("rolepermissions__permission")
    """

    permissions = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "is_system_role",
            "permissions",
            "members_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "members_count"]

    def get_permissions(self, obj) -> list[dict]:
        """
        يُرجع قائمة الصلاحيات بدون N+1.
        يفترض أن rolepermissions مُجلَبة مسبقاً بـ prefetch_related.
        """
        return [
            {"code": rp.permission.code, "name": rp.permission.name}
            for rp in obj.rolepermissions.all()
        ]

    def get_members_count(self, obj) -> int:
        """يُرجع عدد الأعضاء بهذا الدور."""
        return obj.memberships.filter(status="active").count()


class HotelMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer لعرض عضوية مع بيانات المستخدم والدور.

    ⚠️ N+1 المحتمل:
        يعرض user + role + permissions.
        يتطلب في الـ view:
            .select_related("user", "role")
            .prefetch_related("role__rolepermissions__permission")

    الـ response:
    {
        "id": "uuid",
        "user": {email, full_name, ...},
        "role": {name, permissions: [...]},
        "status": "active",
        "joined_at": "..."
    }
    """

    user = UserSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    role_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = HotelMembership
        fields = [
            "id",
            "user",
            "role",
            "role_id",
            "status",
            "joined_at",
            "permission_codes",
        ]
        read_only_fields = ["id", "joined_at", "user"]

    def get_permission_codes(self, obj) -> list[str]:
        """
        يُرجع قائمة أكواد الصلاحيات مباشرةً بدون N+1.
        يفترض prefetch_related("role__rolepermissions__permission").
        """
        if not obj.role:
            return []
        return [rp.permission.code for rp in obj.role.rolepermissions.all()]


class ActiveHotelSelectionSerializer(serializers.Serializer):
    """
    Serializer لتحديد الفندق النشط للمستخدم.
    يُستخدم في endpoint: POST /api/v1/auth/select-hotel/
    """

    hotel_id = serializers.UUIDField(
        help_text="UUID of the hotel to set as active context",
    )

    def validate_hotel_id(self, value):
        """تتحقق من أن المستخدم عضو في هذا الفندق."""
        user = self.context["request"].user
        from accounts.models import HotelMembership
        if not HotelMembership.objects.filter(
            user=user,
            hotel_id=value,
            status="active",
        ).exists():
            raise ValidationError("You are not an active member of this hotel.")
        return value
