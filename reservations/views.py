"""
reservations/views.py
=====================
المسار: reservations/views.py
Phase: 5 — Reservations + Availability Engine
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from rooms.serializers import RoomSerializer
from reservations.models import Reservation, ReservationRoom
from reservations.selectors import (
    get_reservations, get_reservation_by_id, get_available_rooms_for_dates
)
from reservations.services import ReservationService
from reservations.serializers import (
    ReservationSerializer, ReservationCreateSerializer,
    ReservationStatusUpdateSerializer, RoomUpgradeSerializer,
    AvailabilityQuerySerializer
)
from customers.models import Customer
from rooms.models import BookingSource, Room


# ---------------------------------------------------------------------------
# Availability View
# ---------------------------------------------------------------------------

@extend_schema(
    summary="Check room availability for given dates",
    tags=["Reservations - Availability"],
)
class AvailabilityView(APIView):
    """
    GET /api/v1/reservations/availability/?check_in=...&check_out=...&room_type_id=...
    """
    permission_classes = [IsAuthenticated, IsHotelMember]

    def get(self, request):
        serializer = AvailabilityQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        available_rooms = get_available_rooms_for_dates(
            hotel=request.hotel,
            check_in=data["check_in"],
            check_out=data["check_out"],
            room_type_id=data.get("room_type_id"),
        )
        return Response({
            "check_in": data["check_in"],
            "check_out": data["check_out"],
            "available_rooms": RoomSerializer(available_rooms, many=True).data,
            "count": available_rooms.count(),
        })


# ---------------------------------------------------------------------------
# Reservation ViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="List reservations", tags=["Reservations"]),
    create=extend_schema(summary="Create reservation", tags=["Reservations"]),
    retrieve=extend_schema(summary="Get reservation detail", tags=["Reservations"]),
    destroy=extend_schema(summary="Cancel reservation", tags=["Reservations"]),
)
class ReservationViewSet(viewsets.ModelViewSet):
    """Full reservation CRUD + status transitions."""
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "customer"]
    ordering_fields = ["check_in", "check_out", "created_at", "total_price"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return get_reservations(
            hotel=self.request.hotel,
            status=self.request.query_params.get("status"),
            customer_id=self.request.query_params.get("customer"),
            check_in_from=self.request.query_params.get("check_in_from"),
            check_in_to=self.request.query_params.get("check_in_to"),
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreateSerializer
        return ReservationSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("reservations.view")]
        return [IsAuthenticated(), HasHotelPermission("reservations.manage")]

    def create(self, request, *args, **kwargs):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve customer
        try:
            customer = Customer.objects.for_hotel(request.hotel).get(id=data["customer"])
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found in this hotel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve booking source (optional)
        booking_source = None
        if data.get("booking_source"):
            try:
                booking_source = BookingSource.objects.for_hotel(request.hotel).get(
                    id=data["booking_source"]
                )
            except BookingSource.DoesNotExist:
                pass

        # Build rooms_data (convert UUIDs to proper format)
        rooms_data = []
        for r in data["rooms"]:
            rooms_data.append({
                "room_id": r.get("room_id"),
                "adults": r.get("adults", 1),
                "children": r.get("children", 0),
                "notes": r.get("notes", ""),
                "check_in": r.get("check_in", data["check_in"]),
                "check_out": r.get("check_out", data["check_out"]),
            })

        reservation = ReservationService.create(
            hotel=request.hotel,
            customer=customer,
            check_in=data["check_in"],
            check_out=data["check_out"],
            rooms_data=rooms_data,
            booking_source=booking_source,
            adults=data["adults"],
            children=data["children"],
            currency=data["currency"],
            special_requests=data.get("special_requests", ""),
            internal_notes=data.get("internal_notes", ""),
            created_by=request.user,
        )
        return Response(
            ReservationSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """DELETE = Cancel (not hard delete)."""
        reservation = get_reservation_by_id(request.hotel, kwargs["pk"])
        reservation = ReservationService.cancel(reservation, reason="Cancelled via API")
        return Response(ReservationSerializer(reservation).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """
        PATCH /reservations/{id}/status/
        {"action": "confirm"|"cancel"|"check_in"|"check_out"|"no_show", "reason": "..."}
        """
        reservation = get_reservation_by_id(request.hotel, pk)
        serializer = ReservationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        action_map = {
            "confirm": lambda: ReservationService.confirm(reservation),
            "cancel": lambda: ReservationService.cancel(reservation, reason=reason),
            "check_in": lambda: ReservationService.check_in(reservation),
            "check_out": lambda: ReservationService.check_out(reservation),
            "no_show": lambda: ReservationService.no_show(reservation),
        }

        result = action_map[action_name]()
        return Response(ReservationSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="upgrade-room")
    def upgrade_room(self, request, pk=None):
        """POST /reservations/{id}/upgrade-room/ — ترقية/تغيير غرفة."""
        reservation = get_reservation_by_id(request.hotel, pk)
        serializer = RoomUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            res_room = reservation.reservation_rooms.filter(
                deleted_at__isnull=True
            ).get(id=data["reservation_room_id"])
        except ReservationRoom.DoesNotExist:
            return Response(
                {"error": "ReservationRoom not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            new_room = Room.objects.for_hotel(request.hotel).get(id=data["new_room_id"])
        except Room.DoesNotExist:
            return Response(
                {"error": "New room not found in this hotel."},
                status=status.HTTP_404_NOT_FOUND,
            )

        updated = ReservationService.upgrade_room(
            reservation_room=res_room,
            new_room=new_room,
            reason=data.get("reason", ""),
            changed_by=request.user,
        )
        return Response(ReservationSerializer(get_reservation_by_id(request.hotel, pk)).data)
