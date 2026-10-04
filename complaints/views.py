"""complaints/views.py — Phase 7"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from complaints.models import CustomerComplaint
from complaints.services import ComplaintService
from complaints.serializers import CustomerComplaintSerializer, ComplaintCreateSerializer
from customers.models import Customer, Employee
from reservations.models import Reservation


class CustomerComplaintViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "priority", "category"]
    ordering_fields = ["priority", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            CustomerComplaint.objects
            .for_hotel(self.request.hotel)
            .select_related("customer", "assigned_to__user", "reservation")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        return CustomerComplaintSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("complaints.view")]
        return [IsAuthenticated(), HasHotelPermission("complaints.manage")]

    def create(self, request, *args, **kwargs):
        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            customer = Customer.objects.for_hotel(request.hotel).get(id=data["customer"])
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found."}, status=404)

        reservation = None
        if data.get("reservation"):
            try:
                reservation = Reservation.objects.for_hotel(request.hotel).get(id=data["reservation"])
            except Reservation.DoesNotExist:
                pass

        assigned_to = None
        if data.get("assigned_to"):
            try:
                assigned_to = Employee.objects.for_hotel(request.hotel).get(id=data["assigned_to"])
            except Employee.DoesNotExist:
                pass

        complaint = ComplaintService.create(
            hotel=request.hotel,
            customer=customer,
            title=data["title"],
            description=data["description"],
            category=data.get("category", ""),
            priority=data["priority"],
            reservation=reservation,
            assigned_to=assigned_to,
        )
        return Response(CustomerComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="resolve")
    def resolve(self, request, pk=None):
        complaint = self.get_object()
        resolution_notes = request.data.get("resolution_notes", "")
        result = ComplaintService.resolve(complaint, resolution_notes=resolution_notes)
        return Response(CustomerComplaintSerializer(result).data)

    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        complaint = self.get_object()
        emp_id = request.data.get("employee_id")
        try:
            employee = Employee.objects.for_hotel(request.hotel).get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)
        result = ComplaintService.assign(complaint, employee)
        return Response(CustomerComplaintSerializer(result).data)
