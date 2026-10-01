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
from django.utils.text import slugify
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
        if not user:
            password = data.get("password") or "TempPass123!"
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
    GET  /api/v1/auth/me/   → بيانات المستخدم الحالي
    PATCH /api/v1/auth/me/  → تعديل بيانات المستخدم
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Get current user")
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({"success": True, "data": serializer.data})

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
    طلب إعادة تعيين كلمة المرور (يُرسل email).

    ⚠️ لا نُخبر المستخدم إذا كان الـ email موجوداً أم لا (security best practice).
    """

    permission_classes = [AllowAny]

    @extend_schema(tags=["auth"], request=PasswordResetRequestSerializer, summary="Request password reset")
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True)
            # TODO: إرسال email (يُفعَّل في Phase 8 مع Celery)
            logger.info("Password reset requested", extra={"email": email, "user_id": str(user.id)})
        except User.DoesNotExist:
            # لا نُخبر المستخدم إذا كان الـ email غير موجود
            pass

        return Response({
            "success": True,
            "message": "If this email exists, a reset link has been sent.",
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
