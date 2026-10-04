"""
rooms/views.py
==============
المسار: rooms/views.py
Phase: 4 — Master Data

Views:
  - LanguageViewSet       → Global languages (platform admin only)
  - HotelLanguageViewSet  → Hotel-specific language config
  - BookingSourceViewSet  → Hotel booking sources
  - RoomTypeViewSet       → Room categories with translations
  - RoomViewSet           → Individual rooms + status update action
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from common.permissions.hotel_permissions import (
    IsHotelMember, HasHotelPermission, IsPlatformAdmin
)
from rooms.models import Language, HotelLanguage, BookingSource, RoomType, Room
from rooms.selectors import (
    get_all_active_languages, get_hotel_languages, get_booking_sources,
    get_room_types, get_rooms, get_room_by_id, get_room_type_by_id,
    get_all_booking_sources
)
from rooms.services import (
    LanguageService, HotelLanguageService, BookingSourceService,
    RoomTypeService, RoomService
)
from rooms.serializers import (
    LanguageSerializer, HotelLanguageSerializer, HotelLanguageWriteSerializer,
    BookingSourceSerializer, RoomTypeSerializer, RoomTypeWriteSerializer,
    RoomSerializer, RoomWriteSerializer, RoomStatusUpdateSerializer
)


# ---------------------------------------------------------------------------
# Language (Global)
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="List all active languages", tags=["Languages"]),
    retrieve=extend_schema(summary="Get language detail", tags=["Languages"]),
    create=extend_schema(summary="Create language (platform admin only)", tags=["Languages"]),
)
class LanguageViewSet(viewsets.ModelViewSet):
    """
    Global language registry.
    Read: any authenticated user.
    Write: platform admin only.
    """
    serializer_class = LanguageSerializer
    filter_backends = [SearchFilter]
    search_fields = ["code", "name"]

    def get_queryset(self):
        return get_all_active_languages()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsPlatformAdmin()]

    def perform_create(self, serializer):
        # Use service layer
        lang = LanguageService.create(
            code=serializer.validated_data["code"],
            name=serializer.validated_data["name"],
            native_name=serializer.validated_data.get("native_name", ""),
            is_rtl=serializer.validated_data.get("is_rtl", False),
        )
        return lang


# ---------------------------------------------------------------------------
# HotelLanguage
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="List hotel languages", tags=["Hotel Languages"]),
    create=extend_schema(summary="Add language to hotel", tags=["Hotel Languages"]),
    destroy=extend_schema(summary="Remove language from hotel", tags=["Hotel Languages"]),
)
class HotelLanguageViewSet(viewsets.ModelViewSet):
    """Hotel-specific language configuration."""
    http_method_names = ["get", "post", "delete", "head", "options"]
    permission_classes = [IsAuthenticated, IsHotelMember]

    def get_serializer_class(self):
        if self.action == "create":
            return HotelLanguageWriteSerializer
        return HotelLanguageSerializer

    def get_queryset(self):
        return get_hotel_languages(self.request.hotel)

    def create(self, request, *args, **kwargs):
        serializer = HotelLanguageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hotel_lang = HotelLanguageService.add_language(
            hotel=request.hotel,
            language_code=serializer.validated_data["language_code"],
            is_default=serializer.validated_data.get("is_default", False),
        )
        return Response(HotelLanguageSerializer(hotel_lang).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# BookingSource
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="List booking sources", tags=["Booking Sources"]),
    create=extend_schema(summary="Create booking source", tags=["Booking Sources"]),
    update=extend_schema(summary="Update booking source", tags=["Booking Sources"]),
    destroy=extend_schema(summary="Delete booking source", tags=["Booking Sources"]),
)
class BookingSourceViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSourceSerializer
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return get_all_booking_sources(self.request.hotel)

    def perform_create(self, serializer):
        return BookingSourceService.create(
            hotel=self.request.hotel,
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        return BookingSourceService.update(
            source=self.get_object(),
            **serializer.validated_data
        )


# ---------------------------------------------------------------------------
# RoomType
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="List room types with translations", tags=["Room Types"]),
    create=extend_schema(summary="Create room type", tags=["Room Types"]),
    update=extend_schema(summary="Update room type", tags=["Room Types"]),
    destroy=extend_schema(summary="Delete room type", tags=["Room Types"]),
)
class RoomTypeViewSet(viewsets.ModelViewSet):
    """Room types with i18n translations."""
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["code"]
    ordering_fields = ["sort_order", "base_price", "created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RoomTypeWriteSerializer
        return RoomTypeSerializer

    def get_queryset(self):
        return get_room_types(self.request.hotel)

    def retrieve(self, request, *args, **kwargs):
        room_type = get_room_type_by_id(request.hotel, kwargs["pk"])
        return Response(RoomTypeSerializer(room_type).data)

    def perform_create(self, serializer):
        data = serializer.validated_data
        translations = data.pop("translations", [])
        return RoomTypeService.create(
            hotel=self.request.hotel,
            translations=translations,
            **data
        )

    def perform_update(self, serializer):
        data = serializer.validated_data
        translations = data.pop("translations", None)
        return RoomTypeService.update(
            room_type=self.get_object(),
            translations=translations,
            **data
        )

    def get_permissions(self):
        if self.action == "list" or self.action == "retrieve":
            return [IsAuthenticated(), IsHotelMember()]
        return [IsAuthenticated(), HasHotelPermission("rooms.manage")]


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="List rooms", tags=["Rooms"]),
    create=extend_schema(summary="Create room", tags=["Rooms"]),
    update=extend_schema(summary="Update room", tags=["Rooms"]),
    destroy=extend_schema(summary="Deactivate room", tags=["Rooms"]),
)
class RoomViewSet(viewsets.ModelViewSet):
    """Individual hotel rooms with status management."""
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "room_type", "floor"]
    search_fields = ["room_number"]
    ordering_fields = ["room_number", "floor", "created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RoomWriteSerializer
        return RoomSerializer

    def get_queryset(self):
        return get_rooms(
            hotel=self.request.hotel,
            status=self.request.query_params.get("status"),
            room_type_id=self.request.query_params.get("room_type"),
            floor=self.request.query_params.get("floor"),
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["hotel"] = self.request.hotel
        return ctx

    def perform_create(self, serializer):
        data = serializer.validated_data
        return RoomService.create(
            hotel=self.request.hotel,
            room_type_id=data["room_type"].id,
            room_number=data["room_number"],
            floor=data.get("floor", 1),
            status=data.get("status", "available"),
            notes=data.get("notes", ""),
        )

    def perform_update(self, serializer):
        return RoomService.update(
            room=self.get_object(),
            **serializer.validated_data
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("rooms.view")]
        return [IsAuthenticated(), HasHotelPermission("rooms.manage")]

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """PATCH /rooms/{id}/status/ — تحديث حالة الغرفة."""
        room = get_room_by_id(request.hotel, pk)
        serializer = RoomStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = RoomService.update_status(
            room=room,
            new_status=serializer.validated_data["status"],
        )
        return Response(RoomSerializer(room).data)
