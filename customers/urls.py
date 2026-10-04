"""
customers/urls.py
=================
المسار: customers/urls.py
Phase: 4 — Master Data
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers.views import CustomerViewSet, EmployeeViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    path("", include(router.urls)),
]
