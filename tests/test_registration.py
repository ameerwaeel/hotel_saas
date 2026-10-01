"""
tests/test_registration.py
===========================
اختبارات الـ Endpoints الخاصة بتسجيل المستخدمين، وإنشاء الفنادق بالمالك،
وإضافة الموظفين، وإدارة المستخدمين من قبل مدير المنصة.
"""

import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from tenants.models import Hotel
from accounts.models import Role, HotelMembership

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """اختبارات تسجيل مستخدم جديد عادي."""

    def test_register_user_success(self, api_client):
        url = "/api/v1/auth/register/"
        data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
            "phone": "+201011223344",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        res_data = response.json()
        assert res_data["success"] is True
        assert "access" in res_data["data"]
        assert "refresh" in res_data["data"]
        assert res_data["data"]["user"]["email"] == "newuser@example.com"
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_duplicate_email(self, api_client, user):
        url = "/api/v1/auth/register/"
        data = {
            "email": user.email,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "first_name": "Duplicate",
            "last_name": "User",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["success"] is False


@pytest.mark.django_db
class TestHotelRegistrationOnboarding:
    """اختبارات تسجيل فندق جديد بالكامل مع مالك الفندق."""

    def test_register_hotel_with_owner_success(self, api_client):
        url = "/api/v1/auth/register-hotel/"
        data = {
            "email": "owner@cairopalace.com",
            "password": "StrongPassword123!",
            "first_name": "Karim",
            "last_name": "Hassan",
            "phone": "+201099887766",
            "hotel_name": "Cairo Palace Hotel",
            "subdomain": "cairo-palace",
            "default_currency": "USD",
            "default_language": "en",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        res_data = response.json()
        assert res_data["success"] is True
        assert "access" in res_data["data"]
        assert res_data["data"]["hotel"]["subdomain"] == "cairo-palace"

        # التأكد من قاعدة البيانات
        hotel = Hotel.objects.get(subdomain="cairo-palace")
        owner = User.objects.get(email="owner@cairopalace.com")
        assert hotel.name == "Cairo Palace Hotel"
        assert hasattr(hotel, "settings")  # تم إنشاؤها عبر الإشارة تلقائياً
        membership = HotelMembership.objects.get(hotel=hotel, user=owner)
        assert membership.role.name == "Owner"
        assert membership.status == "active"

    def test_register_hotel_duplicate_subdomain(self, api_client, hotel_a):
        url = "/api/v1/auth/register-hotel/"
        data = {
            "email": "diffowner@example.com",
            "password": "StrongPassword123!",
            "first_name": "Other",
            "last_name": "Owner",
            "hotel_name": "Another Hotel",
            "subdomain": hotel_a.subdomain,
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestHotelMemberAddition:
    """اختبار إضافة موظف لفندق بواسطة مدير الفندق."""

    def test_add_member_to_hotel_success(self, auth_client, hotel_a, manager_role, membership_a):
        url = "/api/v1/auth/members/"
        data = {
            "email": "receptionist@alpha.com",
            "role_id": str(manager_role.id),
            "first_name": "Mona",
            "last_name": "Sami",
            "password": "TempPassword123!",
        }
        response = auth_client.post(url, data, format="json", HTTP_X_HOTEL_ID=str(hotel_a.id))
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["success"] is True
        assert User.objects.filter(email="receptionist@alpha.com").exists()
        assert HotelMembership.objects.filter(hotel=hotel_a, user__email="receptionist@alpha.com").exists()


@pytest.mark.django_db
class TestPlatformAdminUserManagement:
    """اختبار إدارة المستخدمين من قبل مدير المنصة."""

    def test_admin_create_platform_admin(self, platform_admin_client):
        url = "/api/v1/auth/users/"
        data = {
            "email": "newadmin@saas.com",
            "password": "AdminPassword123!",
            "first_name": "Support",
            "last_name": "Admin",
            "is_platform_admin": True,
            "is_staff": True,
        }
        response = platform_admin_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        created_user = User.objects.get(email="newadmin@saas.com")
        assert created_user.is_platform_admin is True


@pytest.mark.django_db
class TestHotelMemberList:
    """اختبار استعراض موظفي وأعضاء الفندق."""

    def test_list_members_success(self, auth_client, hotel_a, membership_a):
        url = "/api/v1/auth/members/"
        response = auth_client.get(url, HTTP_X_HOTEL_ID=str(hotel_a.id))
        assert response.status_code == status.HTTP_200_OK
        res_data = response.json()
        assert res_data["success"] is True
        assert len(res_data["data"]) >= 1
        assert res_data["data"][0]["hotel_id"] == str(hotel_a.id)
        assert res_data["data"][0]["hotel_name"] == hotel_a.name



@pytest.mark.django_db
class TestPasswordResetFlow:
    """اختبار دورة إعادة تعيين كلمة المرور كاملة عبر الـ API."""

    def test_password_reset_request_and_confirm_flow(self, api_client, user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        # 1. طلب إعادة تعيين كلمة المرور
        request_url = "/api/v1/auth/reset-password/"
        req_res = api_client.post(request_url, {"email": user.email}, format="json")
        assert req_res.status_code == status.HTTP_200_OK
        assert req_res.json()["success"] is True

        # 2. توليد token و uid للمستخدم
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # 3. تأكيد إعادة تعيين كلمة المرور
        confirm_url = "/api/v1/auth/reset-password-confirm/"
        confirm_data = {
            "uid": uid,
            "token": token,
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }
        confirm_res = api_client.post(confirm_url, confirm_data, format="json")
        assert confirm_res.status_code == status.HTTP_200_OK
        assert confirm_res.json()["success"] is True

        # 4. التحقق من القدرة على تسجيل الدخول بكلمة المرور الجديدة
        login_url = "/api/v1/auth/login/"
        login_res = api_client.post(login_url, {"email": user.email, "password": "NewSecurePassword456!"}, format="json")
        assert login_res.status_code == status.HTTP_200_OK
        assert login_res.json()["success"] is True

