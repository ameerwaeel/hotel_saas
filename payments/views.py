"""
payments/views.py
=================
المسار: payments/views.py
Phase: 6 — Payments
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from payments.models import PaymentMethod, Payment
from payments.services import PaymentMethodService, PaymentService
from payments.serializers import PaymentMethodSerializer, PaymentSerializer, PaymentCreateSerializer
from reservations.models import Reservation


def _get_payments_qs(hotel):
    return (
        Payment.objects
        .for_hotel(hotel)
        .filter(deleted_at__isnull=True)
        .select_related("reservation__customer", "method", "processed_by")
        .order_by("-payment_date", "-created_at")
    )


@extend_schema_view(
    list=extend_schema(summary="List payment methods", tags=["Payments"]),
    create=extend_schema(summary="Create payment method", tags=["Payments"]),
)
class PaymentMethodViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated, IsHotelMember]

    def get_queryset(self):
        return PaymentMethod.objects.for_hotel(self.request.hotel).filter(is_active=True)

    def perform_create(self, serializer):
        return PaymentMethodService.create(
            hotel=self.request.hotel,
            **serializer.validated_data,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("payments.view")]
        return [IsAuthenticated(), HasHotelPermission("payments.manage")]


@extend_schema_view(
    list=extend_schema(summary="List payments", tags=["Payments"]),
    create=extend_schema(summary="Record payment", tags=["Payments"]),
    retrieve=extend_schema(summary="Get payment detail", tags=["Payments"]),
)
class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "currency", "payment_date"]
    ordering_fields = ["payment_date", "amount", "created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return _get_payments_qs(self.request.hotel)

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("payments.view")]
        return [IsAuthenticated(), HasHotelPermission("payments.manage")]

    def create(self, request, *args, **kwargs):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve method
        try:
            method = PaymentMethod.objects.for_hotel(request.hotel).get(id=data["method"])
        except PaymentMethod.DoesNotExist:
            return Response({"error": "Payment method not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve reservation (optional)
        reservation = None
        if data.get("reservation"):
            try:
                reservation = Reservation.objects.for_hotel(request.hotel).get(id=data["reservation"])
            except Reservation.DoesNotExist:
                return Response({"error": "Reservation not found."}, status=status.HTTP_400_BAD_REQUEST)

        payment = PaymentService.create(
            hotel=request.hotel,
            method=method,
            amount=data["amount"],
            currency=data["currency"],
            payment_date=data["payment_date"],
            reservation=reservation,
            reference=data.get("reference", ""),
            notes=data.get("notes", ""),
            processed_by=request.user,
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="refund")
    def refund(self, request, pk=None):
        """POST /payments/{id}/refund/"""
        payment = self.get_object()
        reason = request.data.get("reason", "")
        updated = PaymentService.refund(payment, reason=reason)
        return Response(PaymentSerializer(updated).data)
