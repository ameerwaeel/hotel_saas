"""
accounts/urls.py
=================
المسار: accounts/urls.py
الوظيفة: URL patterns لـ Auth endpoints.

URLs:
  POST   /api/v1/auth/login/           → LoginView
  POST   /api/v1/auth/logout/          → LogoutView
  POST   /api/v1/auth/token/refresh/   → TokenRefreshView (simplejwt)
  GET    /api/v1/auth/me/              → MeView
  PATCH  /api/v1/auth/me/              → MeView
  POST   /api/v1/auth/change-password/ → PasswordChangeView
  POST   /api/v1/auth/reset-password/  → PasswordResetRequestView
  POST   /api/v1/auth/select-hotel/    → SelectHotelView
  GET    /api/v1/auth/my-hotels/       → MyHotelsView
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    LogoutView,
    RegisterView,
    RegisterHotelView,
    AddHotelMemberView,
    UserManagementViewSet,
    MeView,
    PasswordChangeView,
    PasswordResetRequestView,
    SelectHotelView,
    MyHotelsView,
)

app_name = "accounts"

router = DefaultRouter()
router.register(r"users", UserManagementViewSet, basename="user-management")

urlpatterns = [
    # Registration & Onboarding
    path("register/", RegisterView.as_view(), name="register"),
    path("register-hotel/", RegisterHotelView.as_view(), name="register-hotel"),
    path("members/", AddHotelMemberView.as_view(), name="add-member"),

    # Authentication
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Profile
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", PasswordChangeView.as_view(), name="change-password"),
    path("reset-password/", PasswordResetRequestView.as_view(), name="reset-password"),

    # Hotel Context
    path("select-hotel/", SelectHotelView.as_view(), name="select-hotel"),
    path("my-hotels/", MyHotelsView.as_view(), name="my-hotels"),

    # Platform Admin User Management
    path("", include(router.urls)),
]
