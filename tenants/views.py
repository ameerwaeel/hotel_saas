"""
tenants/views.py
=================
المسار: tenants/views.py
الوظيفة: Hotel ViewSet للـ CRUD operations.

⚠️ Platform Admins فقط يمكنهم إنشاء/تعديل الفنادق.
   العمليات العادية للمستخدمين تكون عبر /auth/my-hotels/.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from common.permissions.hotel_permissions import IsPlatformAdmin
from .models import Hotel
from .serializers import HotelSerializer, HotelCreateSerializer


class HotelViewSet(viewsets.ModelViewSet):
    """
    ViewSet لإدارة الفنادق (Platform Admin فقط).

    ⚠️ N+1 محلول: select_related("settings")
    """

    queryset = Hotel.objects.select_related("settings").order_by("name")
    permission_classes = [IsPlatformAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return HotelCreateSerializer
        return HotelSerializer

    def perform_create(self, serializer):
        hotel = serializer.save()
        # إنشاء HotelSettings تلقائياً
        from .models import HotelSettings
        HotelSettings.objects.get_or_create(hotel=hotel)
