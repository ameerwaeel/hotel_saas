"""
common/pagination/pagination.py
================================
المسار: common/pagination/pagination.py
الوظيفة: Pagination class موحدة لكل الـ ViewSets في المشروع.
         مُعرَّفة في REST_FRAMEWORK settings كـ DEFAULT_PAGINATION_CLASS.

الشكل الموحد لـ response:
{
    "success": true,
    "count": 150,          // إجمالي النتائج
    "total_pages": 8,      // إجمالي الصفحات
    "current_page": 1,     // الصفحة الحالية
    "page_size": 20,       // حجم الصفحة
    "next": "http://...?page=2",     // رابط الصفحة التالية (null إذا آخر صفحة)
    "previous": null,                // رابط الصفحة السابقة (null إذا أول صفحة)
    "results": [...]       // البيانات
}

⚠️ مشكلة Django المعروفة: إذا لم تُحدَّد Pagination موحدة من البداية،
   كل view ستستخدم pagination مختلفة → frontend لا يستطيع التعامل معها بشكل موحد.
   الحل: تحديد HotelSaaSPagination كـ DEFAULT في settings من اليوم الأول.
"""

import math
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class HotelSaaSPagination(PageNumberPagination):
    """
    Pagination class موحدة لكل endpoints في Hotel SaaS.

    Parameters من الـ request:
        ?page=1           # رقم الصفحة (يبدأ من 1)
        ?page_size=20     # حجم الصفحة (max: 100)

    Attributes:
        page_size: الحجم الافتراضي للصفحة (من settings)
        page_size_query_param: اسم الـ query parameter لتغيير حجم الصفحة
        max_page_size: الحد الأقصى لحجم الصفحة (منع استدعاء بيانات كبيرة جداً)
        page_query_param: اسم الـ query parameter لرقم الصفحة
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        """
        بناء الـ response الموحد مع معلومات الـ pagination.

        Args:
            data: البيانات المُصفَّحة (list)

        Returns:
            Response بالشكل الموحد
        """
        total_pages = math.ceil(self.page.paginator.count / self.get_page_size(self.request)) if self.get_page_size(self.request) else 1

        return Response({
            "success": True,
            "count": self.page.paginator.count,
            "total_pages": total_pages,
            "current_page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })

    def get_paginated_response_schema(self, schema):
        """Schema للـ OpenAPI documentation (drf-spectacular)."""
        return {
            "type": "object",
            "required": ["success", "count", "total_pages", "current_page", "page_size", "results"],
            "properties": {
                "success": {"type": "boolean", "example": True},
                "count": {"type": "integer", "example": 150},
                "total_pages": {"type": "integer", "example": 8},
                "current_page": {"type": "integer", "example": 1},
                "page_size": {"type": "integer", "example": 20},
                "next": {"type": "string", "nullable": True, "example": "http://api.example.com/api/v1/rooms/?page=2"},
                "previous": {"type": "string", "nullable": True, "example": None},
                "results": schema,
            },
        }
