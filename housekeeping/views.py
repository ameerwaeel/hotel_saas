"""
housekeeping/views.py — Phase 7
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from housekeeping.models import RoomCleaning
from housekeeping.services import HousekeepingService
from housekeeping.serializers import RoomCleaningSerializer, CleaningActionSerializer
from customers.models import Employee


class RoomCleaningViewSet(viewsets.ModelViewSet):
    """Housekeeping management — cleaning tasks lifecycle."""
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "room"]
    ordering_fields = ["created_at"]
    serializer_class = RoomCleaningSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return (
            RoomCleaning.objects
            .for_hotel(self.request.hotel)
            .select_related("room__room_type", "assigned_to__user", "reservation")
            .order_by("-created_at")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("housekeeping.view")]
        return [IsAuthenticated(), HasHotelPermission("housekeeping.manage")]

    def perform_create(self, serializer):
        serializer.save(hotel=self.request.hotel)

    @action(detail=True, methods=["patch"], url_path="action")
    def cleaning_action(self, request, pk=None):
        """
        PATCH /housekeeping/cleanings/{id}/action/
        {"action": "start"|"complete"|"inspect", "employee_id": "..."}
        """
        cleaning = self.get_object()
        serializer = CleaningActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        act = serializer.validated_data["action"]

        if act == "start":
            result = HousekeepingService.start_cleaning(cleaning)
        elif act == "complete":
            result = HousekeepingService.complete_cleaning(cleaning)
        elif act == "inspect":
            result = HousekeepingService.inspect_cleaning(cleaning)

        return Response(RoomCleaningSerializer(result).data)
