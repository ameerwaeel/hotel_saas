"""
rooms/urls.py
=============
المسار: rooms/urls.py
Phase: 4 — Master Data

Endpoints:
  GET/POST     /api/v1/rooms/languages/                  → LanguageViewSet
  GET/DELETE   /api/v1/rooms/languages/{id}/
  GET/POST     /api/v1/rooms/hotel-languages/            → HotelLanguageViewSet
  DELETE       /api/v1/rooms/hotel-languages/{id}/
  GET/POST     /api/v1/rooms/booking-sources/            → BookingSourceViewSet
  GET/PUT/DEL  /api/v1/rooms/booking-sources/{id}/
  GET/POST     /api/v1/rooms/room-types/                 → RoomTypeViewSet
  GET/PUT/DEL  /api/v1/rooms/room-types/{id}/
  GET/POST     /api/v1/rooms/rooms/                      → RoomViewSet
  GET/PUT/DEL  /api/v1/rooms/rooms/{id}/
  PATCH        /api/v1/rooms/rooms/{id}/status/          → RoomViewSet.update_status
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rooms.views import (
    LanguageViewSet, HotelLanguageViewSet, BookingSourceViewSet,
    RoomTypeViewSet, RoomViewSet
)

router = DefaultRouter()
router.register(r"languages", LanguageViewSet, basename="language")
router.register(r"hotel-languages", HotelLanguageViewSet, basename="hotel-language")
router.register(r"booking-sources", BookingSourceViewSet, basename="booking-source")
router.register(r"room-types", RoomTypeViewSet, basename="room-type")
router.register(r"rooms", RoomViewSet, basename="room")

urlpatterns = [
    path("", include(router.urls)),
]
