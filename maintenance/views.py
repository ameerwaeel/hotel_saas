"""
maintenance/views.py — Phase 7

⚠️ N+1 Prevention for Room list with has_blocking_issue:
   annotate(Exists(...)) بدل SerializerMethodField per-row.
"""
from django.db.models import Exists, OuterRef
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from maintenance.models import RoomIssue, IssueStatus
from maintenance.services import MaintenanceService
from maintenance.serializers import RoomIssueSerializer, RoomIssueCreateSerializer
from rooms.models import Room
from customers.models import Employee


class RoomIssueViewSet(viewsets.ModelViewSet):
    """
    Maintenance issues management.

    ⚠️ has_blocking_issue flag: annotate على الـ Room queryset (لا per-row query).
    """
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "priority", "blocking", "room"]
    ordering_fields = ["priority", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            RoomIssue.objects
            .for_hotel(self.request.hotel)
            .select_related("room", "assigned_to__user")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return RoomIssueCreateSerializer
        return RoomIssueSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("maintenance.view")]
        return [IsAuthenticated(), HasHotelPermission("maintenance.manage")]

    def create(self, request, *args, **kwargs):
        serializer = RoomIssueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            room = Room.objects.for_hotel(request.hotel).get(id=data["room"])
        except Room.DoesNotExist:
            return Response({"error": "Room not found."}, status=status.HTTP_404_NOT_FOUND)

        assigned_to = None
        if data.get("assigned_to"):
            try:
                assigned_to = Employee.objects.for_hotel(request.hotel).get(id=data["assigned_to"])
            except Employee.DoesNotExist:
                pass

        issue = MaintenanceService.create_issue(
            hotel=request.hotel,
            room=room,
            title=data["title"],
            description=data.get("description", ""),
            priority=data["priority"],
            blocking=data["blocking"],
            assigned_to=assigned_to,
        )
        return Response(RoomIssueSerializer(issue).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="resolve")
    def resolve(self, request, pk=None):
        """PATCH /maintenance/issues/{id}/resolve/"""
        issue = self.get_object()
        notes = request.data.get("notes", "")
        result = MaintenanceService.resolve_issue(issue, notes=notes)
        return Response(RoomIssueSerializer(result).data)

    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        """PATCH /maintenance/issues/{id}/assign/ {"employee_id": "..."}"""
        issue = self.get_object()
        emp_id = request.data.get("employee_id")
        try:
            employee = Employee.objects.for_hotel(request.hotel).get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        result = MaintenanceService.assign_issue(issue, employee)
        return Response(RoomIssueSerializer(result).data)
