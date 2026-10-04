"""housekeeping/urls.py — Phase 7"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from housekeeping.views import RoomCleaningViewSet

router = DefaultRouter()
router.register(r"cleanings", RoomCleaningViewSet, basename="room-cleaning")

urlpatterns = [path("", include(router.urls))]
