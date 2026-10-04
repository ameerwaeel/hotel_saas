"""payments/urls.py — Phase 6"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.views import PaymentMethodViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r"methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"", PaymentViewSet, basename="payment")

urlpatterns = [path("", include(router.urls))]
