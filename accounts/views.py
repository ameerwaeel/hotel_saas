"""
accounts/views.py
==================
المسار: accounts/views.py
الوظيفة: Auth endpoints للتسجيل، الدخول، الخروج، وإدارة العضوية.

Endpoints:
  POST   /api/v1/auth/login/              → تسجيل الدخول (JWT)
  POST   /api/v1/auth/logout/             → تسجيل الخروج (blacklist token)
  POST   /api/v1/auth/token/refresh/      → تجديد الـ access token
  GET    /api/v1/auth/me/                 → بيانات المستخدم الحالي
  PATCH  /api/v1/auth/me/                 → تعديل بيانات المستخدم
  POST   /api/v1/auth/change-password/    → تغيير كلمة المرور
  POST   /api/v1/auth/reset-password/     → طلب إعادة تعيين كلمة المرور
  POST   /api/v1/auth/select-hotel/       → تحديد الفندق النشط
  GET    /api/v1/auth/my-hotels/          → قائمة الفنادق التي ينتمي إليها المستخدم

مشاكل Django المحلولة:
  1. **JWT + Hotel Context:**
     عند select-hotel، نُخزِّن hotel_id في الـ session (لـ TenantMiddleware).
     في Phase 3+: يمكن تضمين hotel_id في JWT payload للـ stateless access.

  2. **Token Blacklisting:**
     عند logout، نضيف الـ refresh token للـ blacklist (simplejwt feature).
     يتطلب rest_framework_simplejwt.token_blacklist في INSTALLED_APPS.
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.text import slugify
from accounts.tasks import send_mail_resilient

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from common.permissions.hotel_permissions import IsPlatformAdmin, IsHotelMember
from .models import HotelMembership, Role
from tenants.models import Hotel
from .serializers import (
    UserSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    RegisterSerializer,
    RegisterHotelSerializer,
    AddHotelMemberSerializer,
    PlatformAdminCreateUserSerializer,
    PlatformAdminUpdateUserSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    HotelMembershipSerializer,
    ActiveHotelSelectionSerializer,
)

User = get_user_model()
logger = logging.getLogger("hotel_saas")


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    تسجيل الدخول والحصول على JWT tokens.

    Request:
        {email: str, password: str}

    Response:
        {access: str, refresh: str, user: {...}}
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=LoginSerializer,
        responses={200: {"description": "Login successful with JWT tokens"}},
        summary="Login",
        description="Authenticate with email and password. Returns JWT access + refresh tokens.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # توليد JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        logger.info(
            "User logged in",
            extra={
                "user_id": str(user.id),
                "request_id": getattr(request, "request_id", None),
            },
        )

        return Response(
            {
                "success": True,
                "data": {
                    "access": access_token,
                    "refresh": refresh_token,
                    "user": UserSerializer(user).data,
                },
            },
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    تسجيل مستخدم جديد عادي في المنصة والحصول على JWT tokens فوراً.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=RegisterSerializer,
        summary="User Registration",
        description="Register a new user account. Returns access and refresh tokens upon success.",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        logger.info("New user registered", extra={"user_id": str(user.id)})

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "data": {
                    "access": access_token,
                    "refresh": refresh_token,
                    "user": UserSerializer(user).data,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterHotelView(APIView):
    """
    POST /api/v1/auth/register-hotel/
    تسجيل فندق جديد بالكامل مع مالك الفندق (Tenant Onboarding).
    يُنشئ الفندق + المالك + دور Owner + عضوية الفندق في عملية ذرية transaction.atomic().
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=RegisterHotelSerializer,
        summary="Register New Hotel (Tenant Onboarding)",
        description="Create a new hotel organization along with its initial owner user in a single atomic transaction.",
    )
    def post(self, request):
        serializer = RegisterHotelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            # 1. إنشاء المستخدم المالك
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data.get("phone", ""),
            )

            # 2. إنشاء الفندق (إشارة tenants/signals.py ستنشئ HotelSettings تلقائياً)
            slug = slugify(data["hotel_name"])
            hotel = Hotel.objects.create(
                name=data["hotel_name"],
                slug=slug,
                subdomain=data["subdomain"].lower(),
                email=data["email"],
                phone=data.get("phone", ""),
                default_currency=data.get("default_currency", "USD"),
                default_language=data.get("default_language", "en"),
                status="active",
                is_active=True,
            )

            # 3. إنشاء دور المالك (Owner) للفندق
            role, _ = Role.objects.get_or_create(
                hotel=hotel,
                name="Owner",
                defaults={"is_system_role": True, "description": "Hotel Owner with full access"},
            )

            # 4. إنشاء العضوية في الفندق
            HotelMembership.objects.create(
                user=user,
                hotel=hotel,
                role=role,
                status="active",
            )

            # 5. حفظ الفندق النشط في جلسة المستخدم
            if hasattr(request, "session"):
                request.session["active_hotel_id"] = str(hotel.id)

            # 6. توليد JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            logger.info("Hotel registered with owner", extra={"hotel_id": str(hotel.id), "user_id": str(user.id)})

            return Response(
                {
                    "success": True,
                    "message": "Hotel and Owner account registered successfully.",
                    "data": {
                        "access": access_token,
                        "refresh": refresh_token,
                        "user": UserSerializer(user).data,
                        "hotel": {
                            "id": str(hotel.id),
                            "name": hotel.name,
                            "subdomain": hotel.subdomain,
                        },
                    },
                },
                status=status.HTTP_201_CREATED,
            )


class AddHotelMemberView(APIView):
    """
    POST /api/v1/auth/members/
    إضافة موظف/عضو جديد للفندق النشط (بواسطة مدير الفندق).
    """


    permission_classes = [IsAuthenticated, IsHotelMember]

    @extend_schema(
        tags=["auth"],
        summary="List Hotel Members",
        description="List all members and their roles for the active hotel.",
    )
    def get(self, request):
        hotel = getattr(request, "hotel", None)
        if not hotel:
            return Response(
                {"success": False, "error": {"code": "TENANT_NOT_FOUND", "message": "No active hotel selected."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        memberships = (
            HotelMembership.objects
            .filter(hotel=hotel)
            .select_related("user", "role")
            .prefetch_related("role__rolepermissions__permission")
            .order_by("user__first_name", "user__email")
        )
        serializer = HotelMembershipSerializer(memberships, many=True)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        tags=["auth"],
        request=AddHotelMemberSerializer,
        summary="Add/Invite Hotel Member",
        description="Add a new or existing user as a member of the active hotel with an assigned role.",
    )
    def post(self, request):
        hotel = getattr(request, "hotel", None)
        if not hotel:
            return Response(
                {"success": False, "error": {"code": "TENANT_NOT_FOUND", "message": "No active hotel selected."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AddHotelMemberSerializer(data=request.data, context={"hotel": hotel})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data["email"].lower()
        role = Role.objects.get(id=data["role_id"], hotel=hotel)

        # التحقق مما إذا كان المستخدم موجوداً مسبقاً، أو إنشاؤه
        user = User.objects.filter(email=email).first()
        is_new_user = False
        password = data.get("password") or "TempPass123!"
        if not user:
            is_new_user = True
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                phone=data.get("phone", ""),
            )

        # التحقق من عدم وجود عضوية سابقة
        if HotelMembership.objects.filter(user=user, hotel=hotel).exists():
            return Response(
                {"success": False, "error": {"code": "CONFLICT", "message": "User is already a member of this hotel."}},
                status=status.HTTP_409_CONFLICT,
            )

        membership = HotelMembership.objects.create(
            user=user,
            hotel=hotel,
            role=role,
            status="active",
        )

        # إرسال بريد دعوة/ترحيب غير متزامن
        subject = f"You have been added to {hotel.name} on HOTEL SaaS"
        body_msg = (
            f"Hello {user.first_name or user.email},\n\n"
            f"You have been granted access to hotel '{hotel.name}' with the role '{role.name}'.\n"
        )
        if is_new_user:
            body_msg += f"Your temporary password is: {password}\nPlease change it upon first login.\n"
        body_msg += "\nWelcome aboard,\nHOTEL SaaS Team"

        send_mail_resilient(
            subject=subject,
            message=body_msg,
            recipient_list=[user.email],
        )

        return Response(
            {
                "success": True,
                "message": "Member added to hotel successfully.",
                "data": HotelMembershipSerializer(membership).data,
            },
            status=status.HTTP_201_CREATED,
        )



class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet لإدارة المستخدمين في المنصة (Platform Admin Only).
    GET /api/v1/auth/users/        -> قائمة المستخدمين
    POST /api/v1/auth/users/       -> إنشاء مستخدم من قبل الأدمن
    GET /api/v1/auth/users/{id}/   -> جلب مستخدم
    PATCH /api/v1/auth/users/{id}/ -> تعديل مستخدم
    DELETE /api/v1/auth/users/{id}/-> حذف مستخدم
    """

    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsPlatformAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return PlatformAdminCreateUserSerializer
        elif self.action in ["update", "partial_update"]:
            return PlatformAdminUpdateUserSerializer
        return UserSerializer


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    تسجيل الخروج وإضافة الـ refresh token للـ blacklist.

    Request:
        {refresh: str}   → الـ refresh token

    ⚠️ الـ access token لا يزال صالحاً حتى انتهاء مدته.
       لحل ذلك في production: استخدم short-lived access tokens (15-60 min).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        summary="Logout",
        description="Blacklist the refresh token to invalidate the session.",
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Refresh token is required."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            # مسح الـ session
            if hasattr(request, "session"):
                request.session.flush()

            logger.info(
                "User logged out",
                extra={"user_id": str(request.user.id)},
            )

            return Response({"success": True, "message": "Logged out successfully."})

        except Exception as e:
            return Response(
                {"success": False, "error": {"code": "INVALID_TOKEN", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    """
    GET  /api/v1/auth/me/   → بيانات المستخدم الحالي مع سياق الفندق النشط
    PATCH /api/v1/auth/me/  → تعديل بيانات المستخدم
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Get current user")
    def get(self, request):
        user_data = UserSerializer(request.user).data
        active_hotel = getattr(request, "hotel", None)
        active_hotel_data = None
        current_role = None
        permissions = []

        if active_hotel:
            active_hotel_data = {
                "id": str(active_hotel.id),
                "name": active_hotel.name,
                "subdomain": active_hotel.subdomain,
            }
            membership = (
                HotelMembership.objects.filter(user=request.user, hotel=active_hotel, status="active")
                .select_related("role")
                .prefetch_related("role__rolepermissions__permission")
                .first()
            )
            if membership and membership.role:
                current_role = membership.role.name
                permissions = [rp.permission.code for rp in membership.role.rolepermissions.all()]
            elif request.user.is_platform_admin or request.user.is_superuser:

                current_role = "Platform Superadmin"
                permissions = ["*"]

        response_data = {
            **user_data,
            "active_hotel": active_hotel_data,
            "current_role": current_role,
            "permissions": permissions,
        }
        return Response({"success": True, "data": response_data})

    @extend_schema(tags=["auth"], request=UserUpdateSerializer, summary="Update profile")
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": UserSerializer(request.user).data})


class PasswordChangeView(APIView):
    """
    POST /api/v1/auth/change-password/
    تغيير كلمة المرور مع التحقق من القديمة.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], request=PasswordChangeSerializer, summary="Change password")
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        logger.info("Password changed", extra={"user_id": str(request.user.id)})

        return Response({"success": True, "message": "Password changed successfully."})


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/reset-password/
    طلب إعادة تعيين كلمة المرور (يُرسل بريداً إلكترونياً حقيقياً عبر Celery/SMTP).

    ⚠️ لا نُخبر المستخدم إذا كان الـ email موجوداً أم لا (Security Best Practice).
    """

    permission_classes = [AllowAny]

    @extend_schema(tags=["auth"], request=PasswordResetRequestSerializer, summary="Request password reset")
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()

        try:
            user = User.objects.get(email=email, is_active=True)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            subject = "HOTEL SaaS - Password Reset Request"
            message = (
                f"Hello {user.first_name or user.email},\n\n"
                f"We received a request to reset your password for HOTEL SaaS.\n"
                f"Your reset Token is: {token}\n"
                f"Your UID is: {uid}\n\n"
                f"Please submit this token and UID to POST /api/v1/auth/reset-password-confirm/ with your new password.\n"
                f"If you did not request this, please ignore this email.\n"
            )
            html_message = f"""
            <h2>Password Reset Request</h2>
            <p>Hello <strong>{user.first_name or user.email}</strong>,</p>
            <p>We received a request to reset your password for your HOTEL SaaS account.</p>
            <p><strong>UID:</strong> <code>{uid}</code></p>
            <p><strong>Token:</strong> <code>{token}</code></p>
            <p>Submit these in POST <code>/api/v1/auth/reset-password-confirm/</code> with your new password.</p>
            <p>If you did not request this, please ignore this email.</p>
            """
            send_mail_resilient(
                subject=subject,
                message=message,
                recipient_list=[user.email],
                html_message=html_message,
            )
            logger.info("Password reset email queued/sent", extra={"email": email, "user_id": str(user.id)})
        except User.DoesNotExist:
            # لا نُخبر المستخدم إذا كان الـ email غير موجود (Security Best Practice)
            pass

        return Response({
            "success": True,
            "message": "If this email exists in our system, a password reset email has been sent.",
        })


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/reset-password-confirm/
    تأكيد إعادة تعيين كلمة المرور باستخدام uid و token.
    """

    permission_classes = [AllowAny]

    @extend_schema(tags=["auth"], request=PasswordResetConfirmSerializer, summary="Confirm password reset")
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid_b64 = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_id = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"success": False, "error": {"code": "INVALID_TOKEN", "message": "Invalid user ID or token."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"success": False, "error": {"code": "INVALID_TOKEN", "message": "Token is invalid or expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info("Password reset successfully confirmed", extra={"user_id": str(user.id)})

        return Response({
            "success": True,
            "message": "Password has been reset successfully. You can now log in with your new password.",
        })



class SelectHotelView(APIView):
    """
    POST /api/v1/auth/select-hotel/
    تحديد الفندق النشط للمستخدم الحالي.

    يُخزِّن hotel_id في الـ session → TenantMiddleware يحقنه في request.hotel.

    Request:
        {hotel_id: UUID}

    Response:
        {success: true, data: {hotel_id: UUID, hotel_name: str}}
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        request=ActiveHotelSelectionSerializer,
        summary="Select active hotel",
        description="Set the active hotel context for the current session.",
    )
    def post(self, request):
        serializer = ActiveHotelSelectionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        hotel_id = str(serializer.validated_data["hotel_id"])

        # حفظ في الـ session → TenantMiddleware يقرأه
        request.session["active_hotel_id"] = hotel_id
        request.session.save()

        # جلب اسم الفندق للـ response
        from tenants.models import Hotel
        hotel = Hotel.objects.get(id=hotel_id)

        logger.info(
            "Active hotel selected",
            extra={"user_id": str(request.user.id), "hotel_id": hotel_id},
        )

        return Response({
            "success": True,
            "data": {
                "hotel_id": hotel_id,
                "hotel_name": hotel.name,
                "hotel_subdomain": hotel.subdomain,
            },
        })


class MyHotelsView(APIView):
    """
    GET /api/v1/auth/my-hotels/
    قائمة الفنادق التي ينتمي إليها المستخدم الحالي مع أدواره.

    ⚠️ N+1 محلول:
        select_related("hotel", "role")
        prefetch_related("role__rolepermissions__permission")
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="List my hotels")
    def get(self, request):
        memberships = (
            HotelMembership.objects
            .filter(user=request.user, status="active")
            .select_related("hotel", "role")
            .prefetch_related("role__rolepermissions__permission")
            .order_by("hotel__name")
        )

        serializer = HotelMembershipSerializer(memberships, many=True)

        return Response({
            "success": True,
            "data": serializer.data,
        })
