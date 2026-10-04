"""
finance/views.py
================
المسار: finance/views.py
Phase: 6 — Finance + Closings
"""

import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from finance.models import (
    FinanceCategory, FinancialTransaction, ExchangeRate,
    DailyClosing, MonthlyClosing, ClosingStatus
)
from finance.services import FinanceService, ClosingService
from finance.serializers import (
    FinanceCategorySerializer, FinancialTransactionSerializer,
    FinancialTransactionCreateSerializer, ExchangeRateSerializer,
    DailyClosingSerializer, DailyClosingCloseSerializer,
    MonthlyClosingSerializer, DailySummarySerializer
)
from payments.models import PaymentMethod


def _get_transactions_qs(hotel):
    return (
        FinancialTransaction.objects
        .for_hotel(hotel)
        .filter(deleted_at__isnull=True)
        .select_related("category", "method", "reservation", "created_by")
        .order_by("-transaction_date", "-created_at")
    )


class FinanceCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = FinanceCategorySerializer
    permission_classes = [IsAuthenticated, IsHotelMember]

    def get_queryset(self):
        return FinanceCategory.objects.for_hotel(self.request.hotel).filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(hotel=self.request.hotel)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("finance.view")]
        return [IsAuthenticated(), HasHotelPermission("finance.manage")]


class FinancialTransactionViewSet(viewsets.ModelViewSet):
    """
    Transactions: GET=list, POST=create expense/adjustment.
    Income transactions are auto-created when a Payment is recorded.
    """
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["type", "currency", "transaction_date"]
    ordering_fields = ["transaction_date", "amount"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return _get_transactions_qs(self.request.hotel)

    def get_serializer_class(self):
        if self.action == "create":
            return FinancialTransactionCreateSerializer
        return FinancialTransactionSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("finance.view")]
        return [IsAuthenticated(), HasHotelPermission("finance.manage")]

    def create(self, request, *args, **kwargs):
        serializer = FinancialTransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            category = FinanceCategory.objects.for_hotel(request.hotel).get(id=data["category"])
        except FinanceCategory.DoesNotExist:
            return Response({"error": "Finance category not found."}, status=status.HTTP_400_BAD_REQUEST)

        method = None
        if data.get("method"):
            try:
                method = PaymentMethod.objects.for_hotel(request.hotel).get(id=data["method"])
            except PaymentMethod.DoesNotExist:
                pass

        txn = FinanceService.create_expense_transaction(
            hotel=request.hotel,
            category=category,
            amount=data["amount"],
            currency=data["currency"],
            method=method,
            transaction_date=data["transaction_date"],
            notes=data.get("notes", ""),
            created_by=request.user,
        )
        return Response(FinancialTransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated, HasHotelPermission("finance.manage")]

    def get_queryset(self):
        return ExchangeRate.objects.for_hotel(self.request.hotel).order_by("-effective_date")

    def perform_create(self, serializer):
        serializer.save(hotel=self.request.hotel)


class DailySummaryView(APIView):
    """
    GET /api/v1/finance/daily-summary/?date=YYYY-MM-DD
    يُرجع ملخص مالي لليوم مقسَّم حسب العملة.
    """
    permission_classes = [IsAuthenticated, HasHotelPermission("finance.view")]

    def get(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                business_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        else:
            business_date = datetime.date.today()

        summary = FinanceService.get_daily_summary(request.hotel, business_date)

        closing = DailyClosing.objects.filter(
            hotel=request.hotel, business_date=business_date
        ).first()

        return Response({
            "date": business_date,
            "summary_by_currency": summary,
            "closing_status": closing.status if closing else "open",
        })


class DailyClosingViewSet(viewsets.ModelViewSet):
    serializer_class = DailyClosingSerializer
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "business_date"]
    ordering_fields = ["business_date"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return DailyClosing.objects.for_hotel(self.request.hotel).order_by("-business_date")

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("finance.view")]
        return [IsAuthenticated(), HasHotelPermission("finance.manage")]

    def create(self, request, *args, **kwargs):
        """POST /finance/daily-closings/ — إغلاق يوم مالي."""
        serializer = DailyClosingCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        date_str = request.data.get("business_date")
        if not date_str:
            return Response({"error": "business_date is required."}, status=400)
        try:
            business_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response({"error": "Invalid date format."}, status=400)

        closing = ClosingService.close_daily(
            hotel=request.hotel,
            business_date=business_date,
            closed_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(DailyClosingSerializer(closing).data, status=status.HTTP_201_CREATED)


class MonthlyClosingViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyClosingSerializer
    permission_classes = [IsAuthenticated, HasHotelPermission("finance.manage")]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return MonthlyClosing.objects.for_hotel(self.request.hotel).order_by("-year", "-month")

    def create(self, request, *args, **kwargs):
        """POST /finance/monthly-closings/ {"year": 2026, "month": 9}"""
        year = request.data.get("year")
        month = request.data.get("month")
        if not year or not month:
            return Response({"error": "year and month are required."}, status=400)

        closing = ClosingService.close_monthly(
            hotel=request.hotel,
            year=int(year),
            month=int(month),
            closed_by=request.user,
        )
        return Response(MonthlyClosingSerializer(closing).data, status=status.HTTP_201_CREATED)


class ExportFinancialReportView(APIView):
    """POST /api/v1/finance/export/ — تصدير تقرير مالي (Celery task)."""
    permission_classes = [IsAuthenticated, HasHotelPermission("finance.manage")]

    def post(self, request):
        from finance.tasks import export_financial_report
        year = request.data.get("year")
        month = request.data.get("month")
        report_type = request.data.get("report_type", "pdf")

        if not year or not month:
            return Response({"error": "year and month are required."}, status=400)

        task = export_financial_report.delay(
            hotel_id=str(request.hotel.id),
            year=int(year),
            month=int(month),
            report_type=report_type,
        )
        return Response({
            "task_id": task.id,
            "status": "queued",
            "message": "Report generation started. Poll task status for result.",
        }, status=status.HTTP_202_ACCEPTED)
