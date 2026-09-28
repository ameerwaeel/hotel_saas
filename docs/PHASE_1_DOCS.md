# 🟩 Phase 1 — Foundation Infrastructure (البنية التحتية والأساسيات)

المسار في التوثيق: `docs/PHASE_1_DOCS.md`  
الهدف: توحيد شكل الاستجابات وأخطاء النظام وبناء معالج الاستثناءات المركزي ونظام التصفحة والسجلات.

---

## 🛠️ الملفات التي تم إنشاؤها وتعديلها في Phase 1

| اسم الملف | المسار المباشر | الوظيفة والتفاصيل |
| :--- | :--- | :--- |
| `common/exceptions/handlers.py` | [handlers.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/exceptions/handlers.py) | دالة `custom_exception_handler` لتحويل جميع الأخطاء إلى هيكل JSON قياسي ثابت وموحد |
| `common/exceptions/errors.py` | [errors.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/exceptions/errors.py) | حزمة الأخطاء الاستثنائية لمنطق الأعمال مثل `TenantNotFoundError`, `PermissionDeniedError`, `ConflictError` |
| `common/middleware/request_id.py` | [request_id.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/middleware/request_id.py) | `RequestIDMiddleware` لتوليد معرف طلب فريد UUID لكل HTTP Request وطباعته في الـ Header |
| `common/pagination/pagination.py` | [pagination.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/pagination/pagination.py) | كلاس `HotelSaaSPagination` لتوحيد شكل تصفحة القوائم (`count`, `total_pages`, `results`...) |
| `common/logging/formatters.py` | [formatters.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/logging/formatters.py) | كلاس `JSONFormatter` لتحويل كافة سجلات النظام إلى لغة JSON المهيكلة للإنتاج |
| `pytest.ini` | [pytest.ini](file:///c:/Users/smart%20zone/Desktop/hotel_saas/pytest.ini) | إعدادات واختصارات أداة pytest وقراءة بيئة `config.settings.testing` |
| `conftest.py` | [conftest.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/conftest.py) | تجهيز الـ Fixtures المخصصة للاختبارات السريعة (المستخدمين، الفنادق الاختبارية، الـ API Clients) |

---

## 🔍 التفاصيل الفنية الهامة:

### 1. شكل استجابة الأخطاء الموحد (Unified Error Shape):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR | AUTHENTICATION_FAILED | PERMISSION_DENIED | NOT_FOUND",
    "message": "رسالة الخطأ التوضيحية",
    "details": {...},
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 2. التمييز الحرج بين أخطاء المصادقة والصلاحيات:
- **401 `AUTHENTICATION_FAILED`**: يُرجع عندما يكون المستخدم غير مسجل دخول بالأساس.
- **403 `PERMISSION_DENIED`**: يُرجع عندما يكون المستخدم مسجلاً دخول ولكن ليس لديه الصلاحية الكافية لتنفيذ العملية.

---

## 🌐 ملاحظات الفرونت إند (React - Phase 1):
> [!NOTE] أجزاء الفرونت إند المؤجلة لهذه المرحلة:
> - بناء Axios Client مخصص مع Interceptor لمعالجة أخطاء 401 وإعادة التوجيه لصفحة الدخول.
> - إنشاء المكونات المشتركة: `LoadingState`, `ErrorState`, `EmptyState`.
