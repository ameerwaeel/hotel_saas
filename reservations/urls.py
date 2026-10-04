"""
reservations/urls.py
====================
المسار: reservations/urls.py
Phase: 5 — Reservations

Endpoints:
  GET  /api/v1/reservations/availability/        → AvailabilityView
  GET/POST     /api/v1/reservations/             → ReservationViewSet
  GET/PATCH/DEL /api/v1/reservations/{id}/
  PATCH  /api/v1/reservations/{id}/status/       → update_status action
  POST   /api/v1/reservations/{id}/upgrade-room/ → upgrade_room action
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from reservations.views import ReservationViewSet, AvailabilityView

router = DefaultRouter()
router.register(r"", ReservationViewSet, basename="reservation")

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="reservation-availability"),
    path("", include(router.urls)),
]
