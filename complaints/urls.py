"""complaints/urls.py — Phase 7"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from complaints.views import CustomerComplaintViewSet

router = DefaultRouter()
router.register(r"complaints", CustomerComplaintViewSet, basename="customer-complaint")

urlpatterns = [path("", include(router.urls))]
