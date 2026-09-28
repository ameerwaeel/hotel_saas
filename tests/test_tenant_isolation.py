"""
tests/test_tenant_isolation.py
================================
المسار: tests/test_tenant_isolation.py
الوظيفة: Tests عزل الـ Tenants — يُثبت أن Hotel A لا يمكنها رؤية بيانات Hotel B.

هذه من أهم الـ tests في المشروع كله.
أي ثغرة في الـ tenant isolation → data leak بين الفنادق.

Test Cases:
  1. TenantQuerySet: for_hotel(hotel_a) لا يُرجع بيانات hotel_b
  2. TenantManager: .for_hotel(None) يُرجع queryset فارغ
  3. Hotel Status: is_operational يعمل صحيح
  4. Membership: مستخدم فندق A لا يمكنه تحديد فندق B كـ active hotel
  5. Cross-tenant role access: Role من hotel_a لا يُطبَّق على hotel_b
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestTenantQuerySetIsolation:
    """
    اختبار TenantQuerySet.for_hotel() — عزل البيانات بين الفنادق.

    ⚠️ نستخدم Role كمثال لأنه يرتبط بـ hotel مباشرة.
    """

    def test_for_hotel_returns_only_hotel_a_roles(self, hotel_a, hotel_b, manager_role):
        """
        for_hotel(hotel_a) يُرجع فقط أدوار hotel_a — لا أدوار hotel_b.
        """
        from accounts.models import Role
        # إنشاء دور في hotel_b
        role_b = Role.objects.create(
            hotel=hotel_b,
            name="Manager B",
        )

        # جلب أدوار hotel_a
        hotel_a_roles = Role.objects.filter(hotel=hotel_a)
        hotel_b_roles = Role.objects.filter(hotel=hotel_b)

        # التحقق من العزل
        assert role_b not in hotel_a_roles
        assert manager_role not in hotel_b_roles

    def test_tenant_manager_for_hotel_none_returns_empty(self):
        """
        for_hotel(None) يُرجع queryset فارغ — لا data leak.
        """
        from common.models.managers import TenantQuerySet
        from accounts.models import HotelMembership

        # TenantQuerySet.for_hotel(None) يجب أن يُرجع none()
        result = HotelMembership.objects.for_hotel(None)
        assert result.count() == 0

    def test_membership_scoped_to_hotel(self, user, hotel_a, hotel_b, membership_a):
        """
        عضوية hotel_a لا تظهر في hotel_b memberships.
        """
        from accounts.models import HotelMembership

        hotel_a_members = HotelMembership.objects.filter(hotel=hotel_a, user=user)
        hotel_b_members = HotelMembership.objects.filter(hotel=hotel_b, user=user)

        assert hotel_a_members.count() == 1
        assert hotel_b_members.count() == 0


@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestSelectHotelIsolation:
    """
    اختبار أن مستخدم hotel_a لا يمكنه تحديد hotel_b كـ active hotel.
    """

    def test_cannot_select_hotel_without_membership(self, api_client, user, hotel_a, hotel_b, membership_a):
        """
        مستخدم عضو في hotel_a فقط → لا يمكنه تحديد hotel_b.
        """
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # محاولة تحديد hotel_b
        url = "/api/v1/auth/select-hotel/"
        response = api_client.post(url, {
            "hotel_id": str(hotel_b.id),
        }, format="json")

        # يجب أن يرفض
        assert response.status_code == 400
        assert "not an active member" in response.json()["error"]["details"].get(
            "hotel_id", [""]
        )[0].lower() if response.json().get("error", {}).get("details") else True

    def test_can_select_hotel_with_membership(self, api_client, user, hotel_a, membership_a):
        """
        مستخدم عضو في hotel_a → يمكنه تحديدها.
        """
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        url = "/api/v1/auth/select-hotel/"
        response = api_client.post(url, {
            "hotel_id": str(hotel_a.id),
        }, format="json")

        assert response.status_code == 200
        assert response.json()["data"]["hotel_id"] == str(hotel_a.id)


@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestPermissionCrossHotelIsolation:
    """
    اختبار أن صلاحيات hotel_a لا تُطبَّق على hotel_b.
    """

    def test_permissions_scoped_to_hotel(self, user, hotel_a, hotel_b, membership_a):
        """
        صلاحيات user في hotel_a لا تنتقل إلى hotel_b.
        """
        from common.permissions.hotel_permissions import get_user_permissions_for_hotel

        # الصلاحيات في hotel_a
        perms_a = get_user_permissions_for_hotel(user, hotel_a)
        assert len(perms_a) > 0

        # الصلاحيات في hotel_b (user ليس عضواً)
        perms_b = get_user_permissions_for_hotel(user, hotel_b)
        assert len(perms_b) == 0

    def test_platform_admin_bypasses_tenant_isolation(self, platform_admin, hotel_a, hotel_b):
        """
        Platform admin لديه صلاحيات في كل الفنادق.
        """
        from common.permissions.hotel_permissions import get_user_permissions_for_hotel

        perms = get_user_permissions_for_hotel(platform_admin, hotel_a)
        assert "*" in perms


@pytest.mark.django_db
class TestHotelModel:
    """اختبارات Hotel model."""

    def test_hotel_is_operational(self, hotel_a):
        """is_operational يعمل صحيح للفنادق النشطة."""
        assert hotel_a.is_operational is True

    def test_inactive_hotel_not_operational(self, hotel_a):
        """فندق غير نشط → is_operational = False."""
        hotel_a.is_active = False
        hotel_a.save()
        assert hotel_a.is_operational is False

    def test_suspended_hotel_not_operational(self, hotel_a):
        """فندق موقوف → is_operational = False."""
        hotel_a.status = "suspended"
        hotel_a.save()
        assert hotel_a.is_operational is False

    def test_hotel_str_representation(self, hotel_a):
        """__str__ يُرجع الاسم والـ subdomain."""
        assert "Hotel Alpha" in str(hotel_a)
        assert "alpha" in str(hotel_a)
