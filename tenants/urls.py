"""
tenants/urls.py
================
المسار: tenants/urls.py
الوظيفة: URL patterns لـ Hotel/Tenant endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HotelViewSet

app_name = "tenants"

router = DefaultRouter()
router.register(r"hotels", HotelViewSet, basename="hotel")

urlpatterns = [
    path("", include(router.urls)),
]
