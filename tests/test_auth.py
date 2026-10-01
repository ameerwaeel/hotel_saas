"""
tests/test_auth.py
===================
المسار: tests/test_auth.py
الوظيفة: Tests للـ Authentication و RBAC endpoints.

Test Cases:
  1. Login: بيانات صحيحة → JWT tokens
  2. Login: بيانات غلط → 401
  3. Logout: blacklist token
  4. Me: بيانات المستخدم مع JWT
  5. 401 vs 403: التفريق الحرج
  6. HasHotelPermission: صلاحيات صحيحة و غلط
  7. Select Hotel: تحديد الفندق النشط
  8. My Hotels: قائمة الفنادق مع الأدوار
  9. Permission Caching: التحقق من cache
"""

import pytest
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestLogin:
    """اختبارات تسجيل الدخول."""

    def test_login_success(self, api_client, user):
        """بيانات صحيحة → 200 + JWT tokens."""
        url = "/api/v1/auth/login/"
        response = api_client.post(url, {
            "email": "user@test.com",
            "password": "TestPass123!",
        }, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access" in data["data"]
        assert "refresh" in data["data"]
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == "user@test.com"

    def test_login_wrong_password(self, api_client, user):
        """كلمة مرور غلط → 401 (ليس 400)."""
        url = "/api/v1/auth/login/"
        response = api_client.post(url, {
            "email": "user@test.com",
            "password": "WrongPassword!",
        }, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_login_wrong_email(self, api_client):
        """email غير موجود → 401."""
        url = "/api/v1/auth/login/"
        response = api_client.post(url, {
            "email": "notexist@test.com",
            "password": "AnyPass123!",
        }, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client):
        """حقول ناقصة → 400 Validation Error."""
        url = "/api/v1/auth/login/"
        response = api_client.post(url, {"email": "user@test.com"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
class TestLogout:
    """اختبارات تسجيل الخروج."""

    def test_logout_success(self, auth_client, user):
        """logout مع refresh token صحيح → blacklist."""
        refresh = RefreshToken.for_user(user)

        url = "/api/v1/auth/logout/"
        response = auth_client.post(url, {
            "refresh": str(refresh),
        }, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

    def test_logout_without_auth(self, api_client):
        """Logout بدون JWT → 401."""
        url = "/api/v1/auth/logout/"
        response = api_client.post(url, {"refresh": "sometoken"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class Test401vs403Distinction:
    """
    اختبار الفرق الحرج بين 401 و 403.

    ⚠️ هذا من أهم الـ tests في Phase 3:
        - 401: المستخدم غير مسجل → IsAuthenticated فشل
        - 403: المستخدم مسجل لكن ليس له صلاحية → HasHotelPermission فشل
    """

    def test_unauthenticated_request_returns_401(self, api_client):
        """طلب بدون JWT → 401 وليس 403."""
        url = "/api/v1/auth/me/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_authenticated_without_hotel_access_returns_403(self, auth_client):
        """
        طلب بـ JWT صحيح لكن بدون hotel context → 403 وليس 401.
        يُعطي هذا endpoint للـ Platform Admin فقط → user عادي يحصل على 403.
        """
        url = "/api/v1/tenants/hotels/"
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["success"] is False
        # code يجب أن يكون PERMISSION_DENIED وليس AUTHENTICATION_FAILED
        assert data["error"]["code"] == "PERMISSION_DENIED"

    def test_platform_admin_can_access_hotels(self, platform_admin_client):
        """Platform admin يمكنه الوصول لـ hotels endpoint."""
        url = "/api/v1/tenants/hotels/"
        response = platform_admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMeEndpoint:
    """اختبارات GET/PATCH /api/v1/auth/me/"""

    def test_get_me(self, auth_client, user):
        """جلب بيانات المستخدم الحالي."""
        url = "/api/v1/auth/me/"
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["email"] == user.email
        # التأكد من أن كلمة المرور لا تظهر
        assert "password" not in data["data"]

    def test_update_me(self, auth_client, user):
        """تعديل بيانات المستخدم."""
        url = "/api/v1/auth/me/"
        response = auth_client.patch(url, {
            "first_name": "Updated",
            "last_name": "Name",
        }, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["first_name"] == "Updated"

    def test_get_me_with_active_hotel(self, auth_client, user, hotel_a, membership_a):
        """جلب بيانات المستخدم مع سياق الفندق النشط."""
        url = "/api/v1/auth/me/"
        response = auth_client.get(url, HTTP_X_HOTEL_ID=str(hotel_a.id))

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["email"] == user.email
        assert data["active_hotel"] is not None
        assert data["active_hotel"]["id"] == str(hotel_a.id)
        assert data["current_role"] == membership_a.role.name
        assert "rooms.view" in data["permissions"]



@pytest.mark.django_db
class TestSelectHotel:
    """اختبارات select-hotel endpoint."""

    def test_select_valid_hotel(self, auth_client, user, hotel_a, membership_a):
        """تحديد فندق صحيح → 200."""
        url = "/api/v1/auth/select-hotel/"
        response = auth_client.post(url, {
            "hotel_id": str(hotel_a.id),
        }, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["hotel_id"] == str(hotel_a.id)
        assert data["data"]["hotel_name"] == hotel_a.name

    def test_select_hotel_not_member(self, auth_client, user, hotel_b):
        """تحديد فندق المستخدم ليس عضواً فيه → 400."""
        url = "/api/v1/auth/select-hotel/"
        response = auth_client.post(url, {
            "hotel_id": str(hotel_b.id),
        }, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_select_hotel_platform_admin_can_select_any_hotel(self, platform_admin_client, hotel_b):
        """مدير المنصة يمكنه اختيار أي فندق نشط حتى لو لم يكن عضواً عادياً فيه → 200."""
        url = "/api/v1/auth/select-hotel/"
        response = platform_admin_client.post(url, {
            "hotel_id": str(hotel_b.id),
        }, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["hotel_id"] == str(hotel_b.id)
        assert data["data"]["hotel_name"] == hotel_b.name


@pytest.mark.django_db
class TestMyHotels:
    """اختبارات my-hotels endpoint."""

    def test_my_hotels_with_membership(self, auth_client, user, hotel_a, membership_a):
        """المستخدم يرى فنادقه مع الأدوار والصلاحيات."""
        url = "/api/v1/auth/my-hotels/"
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        membership_data = data["data"][0]
        assert "role" in membership_data
        assert "permission_codes" in membership_data
        # التحقق من وجود الصلاحيات
        assert "rooms.view" in membership_data["permission_codes"]

    def test_my_hotels_empty(self, auth_client, user):
        """مستخدم بدون عضوية → قائمة فارغة."""
        url = "/api/v1/auth/my-hotels/"
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"] == []


@pytest.mark.django_db
class TestPermissionCaching:
    """اختبار Permission Caching."""

    def test_permissions_are_cached(self, user, hotel_a, membership_a):
        """التحقق من أن الصلاحيات تُخزَّن في cache."""
        from common.permissions.hotel_permissions import (
            get_user_permissions_for_hotel,
            PERMISSION_CACHE_KEY,
        )

        # مسح الـ cache أولاً
        cache.clear()

        # أول استدعاء → DB query
        perms1 = get_user_permissions_for_hotel(user, hotel_a)

        # التحقق من أن الـ cache يحتوي على النتيجة
        cache_key = PERMISSION_CACHE_KEY.format(user_id=user.id, hotel_id=hotel_a.id)
        cached = cache.get(cache_key)
        assert cached is not None
        assert set(cached) == set(perms1)

    def test_cache_invalidated_on_role_change(self, user, hotel_a, membership_a, staff_role):
        """تغيير الدور → مسح الـ cache."""
        from common.permissions.hotel_permissions import (
            get_user_permissions_for_hotel,
            PERMISSION_CACHE_KEY,
        )

        # جلب الصلاحيات الأولى (Manager → rooms.view + rooms.manage)
        perms_before = get_user_permissions_for_hotel(user, hotel_a)
        assert "rooms.manage" in perms_before

        # تغيير الدور لـ Staff (rooms.view فقط)
        membership_a.role = staff_role
        membership_a.save()  # يُفعِّل signal → يمسح الـ cache

        # التحقق من أن الـ cache فارغ
        cache_key = PERMISSION_CACHE_KEY.format(user_id=user.id, hotel_id=hotel_a.id)
        assert cache.get(cache_key) is None

        # جلب الصلاحيات من جديد (Staff → rooms.view فقط)
        perms_after = get_user_permissions_for_hotel(user, hotel_a)
        assert "rooms.manage" not in perms_after
        assert "rooms.view" in perms_after
