"""maintenance/urls.py — Phase 7"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from maintenance.views import RoomIssueViewSet

router = DefaultRouter()
router.register(r"issues", RoomIssueViewSet, basename="room-issue")

urlpatterns = [path("", include(router.urls))]
