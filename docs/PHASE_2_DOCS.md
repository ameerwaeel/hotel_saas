# 🟪 Phase 2 — Multi-Tenancy + Core Abstract Models (تعدد المستأجرين والنماذج الأصلية)

المسار في التوثيق: `docs/PHASE_2_DOCS.md`  
الهدف: حماية النظام من تسريب البيانات بين الفنادق (Tenant Leakage)، وتطوير النماذج المجرّدة ونماذج الفندق الأساسية.

---

## 🛠️ الملفات التي تم إنشاؤها وتعديلها في Phase 2

| اسم الملف | المسار المباشر | الوظيفة والتفاصيل |
| :--- | :--- | :--- |
| `common/models/base.py` | [base.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/models/base.py) | يحتوي على النماذج المجرّدة: `UUIDModel`, `TimeStampedModel`, `ActiveModel`, `HotelOwnedMixin`, `BaseModel`, `SoftDeleteModel` |
| `common/models/managers.py` | [managers.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/models/managers.py) | يحتوي على `TenantManager` و `TenantQuerySet` لإجبار نطاق الفندق ومنع الاستعلامات المفتوحة غير الآمنة |
| `common/middleware/tenant.py` | [tenant.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/middleware/tenant.py) | `TenantMiddleware` يستخرج الفندق النشط من الجلسة/الـ JWT ويقوم بحقن كائن الفندق في `request.hotel` مع التخزين المؤقت Cache |
| `tenants/models.py` | [models.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tenants/models.py) | يحتوي على كلاس `Hotel` (جذر المستأجر) وكلاس `HotelSettings` (إعدادات التشغيل الحسابية والزمنية) |
| `tenants/serializers.py` | [serializers.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tenants/serializers.py) | محولات البيانات `HotelSerializer`, `HotelSettingsSerializer`, `HotelCreateSerializer` |
| `tenants/views.py` | [views.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tenants/views.py) | كلاس `HotelViewSet` للتحكم بالفنادق وإدارتها لمديري المنصة |
| `tenants/urls.py` | [urls.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tenants/urls.py) | التوجيه الخاص بـ `/api/v1/tenants/hotels/` |
| `tenants/admin.py` | [admin.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tenants/admin.py) | إعدادات لوحة تحكم Django Admin للفنادق والإعدادات |

---

## 🗄️ نماذج قاعدة البيانات (Database Models):

### 1. `Hotel` Model (جذر المستأجر):
- **الحقول**: `id` (UUID), `name`, `slug` (مفهرس فريد), `subdomain` (مفهرس فريد), `email`, `phone`, `address`, `city`, `country`, `timezone`, `default_currency`, `default_language`, `status` (`HotelStatus.choices`), `logo`, `is_active`, `created_at`, `updated_at`.
- **الفهارس (Indexes)**:
  - `models.Index(fields=["status", "is_active"], name="idx_hotel_status_active")`

### 2. `HotelSettings` Model (إعدادات الفندق):
- **العلاقة**: `OneToOneField` مع `Hotel`.
- **الحقول**: `checkin_time`, `checkout_time`, `exchange_rate_mode`, `allow_overbooking`, `max_advance_booking_days`, `auto_close_daily`, `invoice_prefix`.

---

## 🛡️ كيف نمنع تسريب البيانات بين الفنادق (Preventing Tenant Leakage):
1. **الـ Mixin الأصلي (`HotelOwnedMixin`)**: يرغم كل نموذج مملوك للفندق على إضافة `hotel = ForeignKey(..., db_index=True)`.
2. **الـ TenantManager المخصص**: عند استدعاء `.for_hotel(hotel)` يتم التصفية بناءً على مفتاح الفندق، وفي حال تمرير `None` تعيد الاستعلامات نتيجة فارغة `.none()` تلقائياً لحماية البيانات.

---

## 🌐 ملاحظات الفرونت إند (React - Phase 2):
> [!NOTE] أجزاء الفرونت إند المؤجلة لهذه المرحلة:
> - بناء `HotelContext` لربط الفندق النشط حالياً في واجهات المستخدم بقراءة الـ `active_hotel_id`.
