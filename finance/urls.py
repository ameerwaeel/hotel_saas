"""finance/urls.py — Phase 6"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from finance.views import (
    FinanceCategoryViewSet, FinancialTransactionViewSet,
    ExchangeRateViewSet, DailyClosingViewSet, MonthlyClosingViewSet,
    DailySummaryView, ExportFinancialReportView
)

router = DefaultRouter()
router.register(r"categories", FinanceCategoryViewSet, basename="finance-category")
router.register(r"transactions", FinancialTransactionViewSet, basename="financial-transaction")
router.register(r"exchange-rates", ExchangeRateViewSet, basename="exchange-rate")
router.register(r"daily-closings", DailyClosingViewSet, basename="daily-closing")
router.register(r"monthly-closings", MonthlyClosingViewSet, basename="monthly-closing")

urlpatterns = [
    path("daily-summary/", DailySummaryView.as_view(), name="daily-summary"),
    path("export/", ExportFinancialReportView.as_view(), name="finance-export"),
    path("", include(router.urls)),
]
