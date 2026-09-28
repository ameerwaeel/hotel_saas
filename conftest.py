"""
conftest.py
============
المسار: conftest.py (جذر المشروع)
الوظيفة: pytest configuration وـ fixtures المشتركة بين كل الـ tests.

Fixtures الأساسية:
  - api_client: DRF test client
  - hotel_a, hotel_b: فنداقان مختلفان لـ tenant isolation tests
  - user, admin_user, platform_admin: مستخدمون بصلاحيات مختلفة
  - manager_role, staff_role: أدوار مع صلاحيات
  - membership_a: عضوية المستخدم في hotel_a

⚠️ مشكلة Django مع pytest:
   pytest-django يحتاج DJANGO_SETTINGS_MODULE يُعيَّن في pytest.ini أو conftest.py
   نستخدم pytest.ini لأنه أوضح.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def hotel_a(db):
    """
    فندق A للـ tenant isolation tests.
    يُنشئ Hotel + HotelSettings تلقائياً.
    """
    from tenants.models import Hotel, HotelSettings
    hotel = Hotel.objects.create(
        name="Hotel Alpha",
        slug="hotel-alpha",
        subdomain="alpha",
        email="alpha@test.com",
        status="active",
        is_active=True,
    )
    HotelSettings.objects.get_or_create(hotel=hotel)
    return hotel


@pytest.fixture
def hotel_b(db):
    """فندق B للـ tenant isolation tests."""
    from tenants.models import Hotel, HotelSettings
    hotel = Hotel.objects.create(
        name="Hotel Beta",
        slug="hotel-beta",
        subdomain="beta",
        email="beta@test.com",
        status="active",
        is_active=True,
    )
    HotelSettings.objects.get_or_create(hotel=hotel)
    return hotel


@pytest.fixture
def user(db):
    """مستخدم عادي."""
    return User.objects.create_user(
        email="user@test.com",
        username="testuser",
        password="TestPass123!",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db, hotel_a):
    """مستخدم بدور manager في hotel_a."""
    return User.objects.create_user(
        email="admin@test.com",
        username="adminuser",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def platform_admin(db):
    """Platform admin لديه صلاحية كاملة."""
    return User.objects.create_user(
        email="platform@test.com",
        username="platformadmin",
        password="PlatformPass123!",
        is_platform_admin=True,
    )


@pytest.fixture
def rooms_permission(db):
    """صلاحية rooms.view."""
    from accounts.models import Permission
    return Permission.objects.create(
        code="rooms.view",
        name="View Rooms",
        module="rooms",
    )


@pytest.fixture
def rooms_manage_permission(db):
    """صلاحية rooms.manage."""
    from accounts.models import Permission
    return Permission.objects.create(
        code="rooms.manage",
        name="Manage Rooms",
        module="rooms",
    )


@pytest.fixture
def manager_role(db, hotel_a, rooms_permission, rooms_manage_permission):
    """دور Manager في hotel_a مع صلاحيات rooms.view و rooms.manage."""
    from accounts.models import Role, RolePermission
    role = Role.objects.create(
        hotel=hotel_a,
        name="Manager",
        is_system_role=True,
    )
    RolePermission.objects.create(role=role, permission=rooms_permission)
    RolePermission.objects.create(role=role, permission=rooms_manage_permission)
    return role


@pytest.fixture
def staff_role(db, hotel_a, rooms_permission):
    """دور Staff في hotel_a مع صلاحية rooms.view فقط."""
    from accounts.models import Role, RolePermission
    role = Role.objects.create(
        hotel=hotel_a,
        name="Staff",
    )
    RolePermission.objects.create(role=role, permission=rooms_permission)
    return role


@pytest.fixture
def membership_a(db, user, hotel_a, manager_role):
    """عضوية user في hotel_a بدور Manager."""
    from accounts.models import HotelMembership
    return HotelMembership.objects.create(
        user=user,
        hotel=hotel_a,
        role=manager_role,
        status="active",
    )


@pytest.fixture
def auth_client(api_client, user):
    """API client مع JWT token للـ user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def platform_admin_client(api_client, platform_admin):
    """API client مع JWT token للـ platform_admin."""
    refresh = RefreshToken.for_user(platform_admin)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


def authenticate_with_hotel(api_client, user, hotel):
    """
    Helper function: يُعيِّن JWT token ويُعيِّن hotel في الـ session.
    يُحاكي select-hotel flow.
    """
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    # نُعيِّن hotel في request مباشرة لتجاوز TenantMiddleware في tests
    api_client.hotel = hotel
    return api_client
