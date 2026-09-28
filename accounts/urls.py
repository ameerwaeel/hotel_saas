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

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetRequestView,
    SelectHotelView,
    MyHotelsView,
)

app_name = "accounts"

urlpatterns = [
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
]
