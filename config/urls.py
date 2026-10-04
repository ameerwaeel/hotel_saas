"""
config/urls.py
==============
المسار: config/urls.py
الوظيفة: ملف URL الرئيسي للمشروع.
         يجمع كل URL patterns من جميع الـ apps.

هيكل الـ URLs:
  /api/v1/auth/          → accounts app (login, logout, token)
  /api/v1/tenants/       → tenants app (hotel management)
  /api/v1/rooms/         → rooms app
  /api/v1/customers/     → customers app
  /api/v1/reservations/  → reservations app
  /api/v1/payments/      → payments app
  /api/v1/finance/       → finance app
  /api/schema/           → OpenAPI schema (drf-spectacular)
  /api/docs/             → Swagger UI
  /api/redoc/            → ReDoc UI
  /__debug__/            → Django Debug Toolbar (development only)
  /silk/                 → django-silk profiling (development only)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# ---------------------------------------------------------------------------
# API v1 URL patterns
# ---------------------------------------------------------------------------
api_v1_patterns = [
    # 🔐 Authentication & Authorization (Phase 3)
    path("auth/", include("accounts.urls")),
    # 🏨 Tenants & Hotel Management (Phase 2)
    path("tenants/", include("tenants.urls")),
    # 🛏️ Rooms + Languages + BookingSources (Phase 4)
    path("rooms/", include("rooms.urls")),
    # 👥 Customers + Employees (Phase 4)
    path("customers/", include("customers.urls")),
    # 📅 Reservations (Phase 5)
    path("reservations/", include("reservations.urls")),
    # 💳 Payments (Phase 6)
    path("payments/", include("payments.urls")),
    # 💰 Finance (Phase 6)
    path("finance/", include("finance.urls")),
    # 🧹 Housekeeping (Phase 7)
    path("housekeeping/", include("housekeeping.urls")),
    # 🔧 Maintenance (Phase 7)
    path("maintenance/", include("maintenance.urls")),
    # 📋 Complaints (Phase 7)
    path("complaints/", include("complaints.urls")),
]

# ---------------------------------------------------------------------------
# Main URL patterns
# ---------------------------------------------------------------------------
urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),

    # 📚 OpenAPI Schema & Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ---------------------------------------------------------------------------
# Development-only URLs
# ---------------------------------------------------------------------------
if settings.DEBUG:
    # Django Debug Toolbar
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
        path("silk/", include("silk.urls", namespace="silk")),
    ] + urlpatterns
