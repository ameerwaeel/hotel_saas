# 📖 HOTEL SaaS — التوثيق الشامل المكتمل (Phases 0, 1, 2, 3)

المشروع: **HOTEL SaaS Platform**  
مكان التوثيق: `docs/PHASE_0_TO_3_FULL_DOCS.md`  
الهدف: وثيقة مرجعية شاملة لكافة الأكواد، النماذج، الـ APIs، قواعد البيانات، والحلول البرمجية التي تم تطبيقها لمنع المشاكل الشائعة في Django.

---

## 📋 فهرس المحتويات
1. [هيكلية مجلد التوثيق والمشروع](#1-هيكلية-مجلد-التوثيق-والمشروع)
2. [تفاصيل Phase 0 — تجهيز مشروع Django وقواعد البيانات البيئية](#2-تفاصيل-phase-0--تجهيز-مشروع-django-وقواعد-البيانات-البيئية)
3. [تفاصيل Phase 1 — بنية DRF والـ Middleware والـ Exceptions الموحدة](#3-تفاصيل-phase-1--بنية-drf-والـ-middleware-والـ-exceptions-الموحدة)
4. [تفاصيل Phase 2 — Multi-Tenancy ونماذج الفنادق Abstract Models](#4-تفاصيل-phase-2--multi-tenancy-ونماذج-الفنادق-abstract-models)
5. [تفاصيل Phase 3 — Authentication & RBAC والـ Permissions Caching](#5-تفاصيل-phase-3--authentication--rbac-والـ-permissions-caching)
6. [دليل الـ Endpoints والـ Testing Test Suite](#6-دليل-الـ-endpoints-والـ-testing-test-suite)
7. [ملاحظات أجزاء Frontend المعلقة (React/Vite)](#7-ملاحظات-أجزاء-frontend-المعلقة-reactvite)

---

## 1. هيكلية مجلد التوثيق والمشروع

تم إنشاء مجلد خاص باسم `docs/` في جذر المشروع لتجميع كافة ملفات التخطيط وتتبع المهام والتوثيق، بحيث يصبح المرجع الدائم للمشروع:

```
hotel_saas/
├── docs/                               # 📁 مجلد التوثيق العام للمشروع
│   ├── implementation_plan.md          # 📋 خطة البناء والتنفيذ التفصيلية
│   ├── task.md                         # 📝 قائمة تتبع المهام المنجزة والجارية
│   ├── walkthrough.md                  # 🚀 ملخص ملائم للعرض والتأكد من النتائج
│   └── PHASE_0_TO_3_FULL_DOCS.md       # 📖 هذا الملف: التوثيق الفني الشامل والدقيق
```

---

## 2. تفاصيل Phase 0 — تجهيز مشروع Django وقواعد البيانات البيئية

### 📁 الملفات والمسارات التي تم إنشاؤها وتعديلها:
1. `manage.py` — [المسار: `manage.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/manage.py)
   - **الشرح:** مدخل تنفيذ أوامر Django. تم تعديل الإعداد الافتراضي ليقرأ `config.settings.development` بدلاً من المسار القديم.
2. `config/__init__.py` — [المسار: `config/__init__.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/__init__.py)
   - **الشرح:** يقوم بتحميل وتفعيل تطبيق Celery عند بدء تطبيق Django ليعمل بالتوازي مع الإشارات (Signals) المهيأة.
3. `config/celery.py` — [المسار: `config/celery.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/celery.py)
   - **الشرح:** إعداد تطبيق Celery، وتحديد الـ Broker والـ Backend المربوطين بـ Redis، وتفعيل الخاصية `autodiscover_tasks()` لاكتشاف المهام في كل الـ Django Apps تلقائياً.
4. `config/settings/base.py` — [المسار: `config/settings/base.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/base.py)
   - **الشرح:** الإعدادات المركزية المشتركة. تحتوي على:
     - استخدام `django-environ` لقراءة المتغيرات من `.env`.
     - تسجيل جميع التطبيقات Local (`accounts`, `tenants`, `rooms`, `customers`, `reservations`, `payments`, `finance`, إلخ) وتطبيق Custom User Model (`AUTH_USER_MODEL = "accounts.User"`).
     - ضبط REST_FRAMEWORK بالإعدادات الموحدة للـ Exception Handler و Pagination والـ Versioning والـ OpenAPI schema via `drf_spectacular`.
5. `config/settings/development.py` — [المسار: `config/settings/development.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/development.py)
   - **الشرح:** إعدادات بيئة التطوير مع تفعيل `debug_toolbar` و `silk` لفحص استعلامات SQL ومعالجة مشكلة N+1 أثناء التطوير.
6. `config/settings/production.py` — [المسار: `config/settings/production.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/production.py)
   - **الشرح:** إعدادات بيئة الإنتاج الصارمة (HSTS, SSL Redirect, Secure Cookies, Redis Cache).
7. `config/settings/testing.py` — [المسار: `config/settings/testing.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/testing.py)
   - **الشرح:** إعدادات خاصة بالـ Automated Tests (تستخدم SQLite in-memory وتستبعد `debug_toolbar` و `silk` لتجنب أخطاء `djdt` namespace والإسراع في إجراء الفحوصات).
8. `config/urls.py` — [المسار: `config/urls.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/urls.py)
   - **الشرح:** التوجيه الرئيسي للـ APIs `/api/v1/` مع توثيق Swagger (`/api/docs/`) و ReDoc (`/api/redoc/`) و OpenAPI Schema (`/api/schema/`).
9. `.env` & `requirements.txt` — [المسارات: `.env`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/.env) | [`requirements.txt`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/requirements.txt)
   - **الشرح:** تحديد حزم الاعتمادية وقيم المتغيرات الحساسة للبيئة.

---

## 3. تفاصيل Phase 1 — بنية DRF والـ Middleware والـ Exceptions الموحدة

### 📁 الملفات والمسارات:
1. `common/exceptions/handlers.py` — [المسار: `common/exceptions/handlers.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/exceptions/handlers.py)
   - **الشرح:** معالج الاستثناءات المركزية `custom_exception_handler`.
   - **الوظيفة:** تحويل أي خطأ في النظام إلى بنية JSON موحدة تحتوي على:
     ```json
     {
       "success": false,
       "error": {
         "code": "VALIDATION_ERROR | AUTHENTICATION_FAILED | PERMISSION_DENIED | NOT_FOUND",
         "message": "نص الخطأ الواضح",
         "details": {...},
         "request_id": "uuid-v4-string"
       }
     }
     ```
   - **حل مشكلة Django:** التمييز الصريح والدقيق بين خطأ عدم التوثيق **401** (`AUTHENTICATION_FAILED`) وخطأ عدم امتلاك الصلاحية **403** (`PERMISSION_DENIED`).
2. `common/exceptions/errors.py` — [المسار: `common/exceptions/errors.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/exceptions/errors.py)
   - **الشرح:** تعريف استثناءات الأعمال Custom Business Exceptions المخصصة مثل:
     - `TenantNotFoundError`, `TenantAccessDeniedError`, `PermissionDeniedError`, `FeatureNotAvailableError`, `ConflictError`, `InvalidStateTransitionError`, `ClosedPeriodError`.
3. `common/middleware/request_id.py` — [المسار: `common/middleware/request_id.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/middleware/request_id.py)
   - **الشرح:** `RequestIDMiddleware` يقوم بتوليد UUID فريد لكل HTTP Request يمر على النظام وحقنه في `request.request_id` وإعادة طباعته في الـ HTTP Response Header كـ `X-Request-ID` لمتابعة الـ Micro-tracing في الـ Logs.
4. `common/pagination/pagination.py` — [المسار: `common/pagination/pagination.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/pagination/pagination.py)
   - **الشرح:** `HotelSaaSPagination` تفرض Pagination ثابت وموحد لكل ViewSets النظام.
   - **الاستجابة الموحدة:**
     `count`, `total_pages`, `current_page`, `page_size`, `next`, `previous`, `results`.
5. `common/logging/formatters.py` — [المسار: `common/logging/formatters.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/logging/formatters.py)
   - **الشرح:** `JSONFormatter` لتحويل كل السجلات والـ System Logs إلى هيكل JSON منظم في الإنتاج يحتوي على `timestamp`, `level`, `logger`, `message`, `module`, `request_id`, إلخ.

---

## 4. تفاصيل Phase 2 — Multi-Tenancy ونماذج الفنادق Abstract Models

### 📁 الملفات والمسارات:
1. `common/models/base.py` — [المسار: `common/models/base.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/models/base.py)
   - **النماذج المجرّدة (Abstract Models):**
     - `UUIDModel`: استبدال Integer IDs بـ UUID Primary Key لمنع الهجمات وسهولة الربط.
     - `TimeStampedModel`: إضافة `created_at` (مفهرس `db_index=True`) و `updated_at`.
     - `ActiveModel`: إضافة `is_active` (مفهرس `db_index=True`) للفلترة بدلاً من المسح.
     - `HotelOwnedMixin`: ربط أي نموذج بالفندق التابع له عبر `hotel = ForeignKey("tenants.Hotel", on_delete=CASCADE, db_index=True, related_name="%(class)ss")`.
     - `BaseModel`: نموذج جامع يدمج الـ UUID والـ Timestamps والـ Active Flag.
     - `SoftDeleteModel`: إضافة `deleted_at` للنماذج المالية والحساسة.
2. `common/models/managers.py` — [المسار: `common/models/managers.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/models/managers.py)
   - **الشرح:** `TenantQuerySet` و `TenantManager`.
   - **حل مشكلة تسريب البيانات (Tenant Leakage):** يمنع جلب الكائنات بدون تحديد الفندق، ويوفر ميثود أمنية سريعة:
     - `.for_hotel(hotel)`: تصفية نتائج الفندق فقط (إذا مرر `None` تعيد QuerySet فارغ فوراً).
     - `.active()`: تصفية الكائنات النشطة.
     - `.for_hotel_active(hotel)`: تصفية نشطة مخصصة للفندق.
3. `common/middleware/tenant.py` — [المسار: `common/middleware/tenant.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/middleware/tenant.py)
   - **الشرح:** `TenantMiddleware` يستخرج هاتف/معرف الفندق النشط من الجلسة أو الـ JWT payload ويقوم بحقن كائن الفندق في `request.hotel` في كل طلب تلقائياً مع التخزين المؤقت `cache` لمنع كثرة الاستعلامات.
4. `tenants/models.py` — [المسار: `tenants/models.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tenants/models.py)
   - **النماذج المُنشأة:**
     - `Hotel` (يرث `BaseModel`): جذر الـ Tenant.
       - الحقول: `name`, `slug` (مفهرس فريد), `subdomain` (مفهرس فريد), `email`, `phone`, `address`, `city`, `country`, `timezone`, `default_currency`, `default_language`, `status` (`HotelStatus.choices`), `logo`.
       - الفهارس المركبة: `models.Index(fields=["status", "is_active"], name="idx_hotel_status_active")`.
     - `HotelSettings` (يرث `BaseModel`): إعدادات التشغيل الخاصة بالفندق (`OneToOneField` مع `Hotel`).
       - الحقول: `checkin_time`, `checkout_time`, `exchange_rate_mode`, `allow_overbooking`, `max_advance_booking_days`, `auto_close_daily`, `invoice_prefix`.
5. `tenants/serializers.py`, `views.py`, `urls.py`, `admin.py`
   - **الشرح:** إتاحة APIs إدارية للـ Platform Admins للتحكم بالفنادق وإعداداتها، ومنع N+1 عبر `select_related("settings")`.

---

## 5. تفاصيل Phase 3 — Authentication & RBAC والـ Permissions Caching

### 📁 الملفات والمسارات:
1. `accounts/models.py` — [المسار: `accounts/models.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/models.py)
   - **النماذج المحدثة والمصممة:**
     - `User` (يرث `AbstractUser`, `UUIDModel`, `TimeStampedModel`):
       - تسجيل الدخول بواسطة البريد الإلكتروني (`USERNAME_FIELD = "email"`).
       - الحقول: `email` (مفهرس فريد), `phone`, `avatar`, `is_platform_admin`, `preferred_language`.
     - `HotelMembership` (يرث `BaseModel`):
       - ربط المستخدم بالفندق والدور.
       - الحقول: `user` (FK), `hotel` (FK), `role` (FK), `status` (`MembershipStatus.choices`), `joined_at`.
       - القيود والفهارس: `UniqueConstraint(fields=["user", "hotel"])` وفهارس مركبة على `(hotel, status)` و `(user, status)`.
       - المانجر المخصص: يستخدم `TenantManager`.
     - `Role` (يرث `BaseModel`):
       - الأدوار المخصصة داخل الفندق.
       - الحقول: `hotel` (FK), `name`, `description`, `is_system_role`.
       - القيود: `UniqueConstraint(fields=["hotel", "name"])`.
     - `Permission`:
       - الصلاحيات العامة للنظام على مستوى الموديولات (`code` مثل `"rooms.manage"`, `"finance.view"`).
     - `RolePermission`:
       - جدول الربط بين الأدوار والصلاحيات (`UniqueConstraint(fields=["role", "permission"])`).
2. `common/permissions/hotel_permissions.py` — [المسار: `common/permissions/hotel_permissions.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/permissions/hotel_permissions.py)
   - **فئات الصلاحيات المخصصة (DRF Permission Classes):**
     - `IsHotelMember`: التأكد من أن المستخدم عضو نشط في `request.hotel`.
     - `HasHotelPermission(code)`: تقييم صلاحية المستخدم بالنسبة للفندق النشط.
     - `IsHotelAdmin`: اختصار لصلاحية `hotel.admin`.
     - `IsPlatformAdmin`: التحقق من أن المستخدم مدير للمنصة ككل.
   - **حل مشكلة Performance/N+1 للصلاحيات (Permission Caching):**
     - دالة `get_user_permissions_for_hotel(user, hotel)` تقوم بحساب الصلاحيات وتخزينها في Cache تحت المفتاح `"perms:{user_id}:{hotel_id}"` لمدة 5 دقائق.
3. `accounts/signals.py` — [المسار: `accounts/signals.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/signals.py)
   - **مستقبلات الإشارات (Django Signals):**
     - تقوم بمسح وتفريغ الـ Cache فوراً (`invalidate_permission_cache`) عند تعديل أو حذف أي عضوية في `HotelMembership` أو تعديل صلاحية في `RolePermission`.
4. `accounts/serializers.py` — [المسار: `accounts/serializers.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/serializers.py)
   - يحتوي على: `UserSerializer`, `UserUpdateSerializer`, `LoginSerializer`, `PasswordChangeSerializer`, `PasswordResetRequestSerializer`, `RoleSerializer`, `HotelMembershipSerializer`, `ActiveHotelSelectionSerializer`.
   - **منع N+1 في Nested Serializers:** استخدام `SerializerMethodField` والاستعانة بـ `select_related` و `prefetch_related` في Querysets الخاصة بالـ Views.
5. `accounts/views.py` — [المسار: `accounts/views.py`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/views.py)
   - تنفيذ كافة مشاهد Auth المذكورة في الجدول أدناه.

---

## 6. دليل الـ Endpoints والـ Testing Test Suite

### 🌐 جدولة الـ API Endpoints المُنفذة والجاهزة:

| الموديول | الميثود | الـ Endpoint | الوظيفة والشرح | درجة الأمان الصلاحية |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/login/` | تسجيل الدخول بالبريد وكلمة المرور والحصول على JWT Tokens | `AllowAny` |
| **Auth** | `POST` | `/api/v1/auth/logout/` | إبطال الجلسة وتمرير Refresh Token للقائمة السوداء Blacklist | `IsAuthenticated` |
| **Auth** | `POST` | `/api/v1/auth/token/refresh/` | تجديد Access Token بواسطة Refresh Token | `AllowAny` |
| **Auth** | `GET` | `/api/v1/auth/me/` | جلب البيانات الشخصية للمستخدم الحالي | `IsAuthenticated` |
| **Auth** | `PATCH` | `/api/v1/auth/me/` | تعديل البيانات الشخصية للمستخدم الحالي | `IsAuthenticated` |
| **Auth** | `POST` | `/api/v1/auth/change-password/` | تغيير كلمة المرور للمستخدم المسجل | `IsAuthenticated` |
| **Auth** | `POST` | `/api/v1/auth/reset-password/` | طلب إعادة تعيين كلمة المرور عبر البريد | `AllowAny` |
| **Auth** | `POST` | `/api/v1/auth/select-hotel/` | تعيين وتحديد الفندق النشط في الجلسة `request.hotel` | `IsAuthenticated` |
| **Auth** | `GET` | `/api/v1/auth/my-hotels/` | عرض جميع الفنادق التي ينتمي إليها المستخدم وأدواره وصلاحياته | `IsAuthenticated` |
| **Tenants** | `GET/POST` | `/api/v1/tenants/hotels/` | عرض وإنشاء الفنادق بالمنصة | `IsPlatformAdmin` |
| **Tenants** | `GET/PUT/DELETE`| `/api/v1/tenants/hotels/{id}/` | التحكم بالفندق وإعداداته تفصيلياً | `IsPlatformAdmin` |

---

### 🧪 نتائج وتفاصيل الـ Automated Test Suite:

تم إعداد ملفات الاختبار الفردية والمتكاملة داخل مجلد `tests/` وربطها بـ `conftest.py` و `pytest.ini`.

#### 1. ملف `tests/test_auth.py` (17 Tests - Passed ✅):
- `test_login_success`: التحقق من نجاح تسجيل الدخول وإعادة الـ JWT Tokens.
- `test_login_wrong_password`: التحقق من إرجاع 401 عند خطأ كلمة المرور.
- `test_login_wrong_email`: التحقق من إرجاع 401 عند عدم وجود البريد.
- `test_login_missing_fields`: التحقق من إرجاع 400 Validation Error عند عدم إرسال البيانات.
- `test_logout_success`: إدخال Refresh Token في الـ Blacklist.
- `test_logout_without_auth`: رفض تسجيل الخروج بدون Auth Token.
- `test_unauthenticated_request_returns_401`: تأكيد أن الطلب بدون Token يرجع 401 (`AUTHENTICATION_FAILED`).
- `test_authenticated_without_hotel_access_returns_403`: تأكيد أن الطلب بدون صلاحية يرجع 403 (`PERMISSION_DENIED`).
- `test_platform_admin_can_access_hotels`: إتاحة الوصول لمدير المنصة.
- `test_get_me` & `test_update_me`: قراءة وتعديل الملف الشخصي.
- `test_select_valid_hotel` & `test_select_hotel_not_member`: اختيار الفندق واختبار رفض الفنادق التي لا يملك الموظف عضوية فيها.
- `test_my_hotels_with_membership` & `test_my_hotels_empty`: قراءة الفنادق والأدوار والصلاحيات بدون N+1.
- `test_permissions_are_cached` & `test_cache_invalidated_on_role_change`: اختبار التخزين المؤقت للصلاحيات وإبطاله التلقائي عبر الـ Signals.

#### 2. ملف `tests/test_tenant_isolation.py` (11 Tests - Passed ✅):
- `test_for_hotel_returns_only_hotel_a_roles`: التأكد المطلق من عدم اختلاط بيانات الفندق A مع الفندق B.
- `test_tenant_manager_for_hotel_none_returns_empty`: تأكيد أن الاستعلام بدون فندق يرجع نتائج فارغة لحماية البيانات.
- `test_membership_scoped_to_hotel`: تصفية العضويات حسب الفندق.
- `test_cannot_select_hotel_without_membership`: منع اختيار فندق لا يملكه المستخدم.
- `test_permissions_scoped_to_hotel`: التأكد أن صلاحيات الفندق A لا تُطبق على الفندق B.
- `test_platform_admin_bypasses_tenant_isolation`: إتاحة الصلاحية الشاملة لمدير المنصة.
- `test_hotel_is_operational`, `test_inactive_hotel_not_operational`, `test_suspended_hotel_not_operational`, `test_hotel_str_representation`: اختبارات شروط عمل الفندق واستجابته.

**إجمالي الاختبارات الناجحة:** **28 / 28 Passed (100%)**.

---

## 7. ملاحظات أجزاء Frontend المعلقة (React/Vite)

> [!NOTE] بناءً على التوجيهات، تم إرجاء تنفيذ واجهات React/Vite مع ترك الملاحظات والهيكلية التالية لربطها في وقت لاحق:

1. **التهيئة العامة (Phase 0 Frontend Note):**
   - ينبغي إعداد مشروع React باستخدام Vite تحت مجلد `frontend/`.
   - إضافة مكتبات `axios`, `react-router-dom`, `react-i18next`, `lucide-react`.
2. **العميل البرمجي للـ API (Phase 1 Frontend Note):**
   - إعداد Axios Instance يحتوي على Interceptors لالتقاط أخطاء 401 وإعادة التوجيه لصفحة تسجيل الدخول، وأخطاء 403 لإظهار تنبيه الصلاحيات.
   - بناء مكونات مشتركة: `LoadingState`, `ErrorState`, `EmptyState`.
3. **سياق الفندق النشط (Phase 2 Frontend Note):**
   - بناء `HotelContext` في React لمتابعة الفندق النشط حالياً وقراءة `active_hotel_id` من `localStorage` أو الجلسة.
4. **أمان الواجهة والأدوار (Phase 3 Frontend Note):**
   - بناء custom hook باسم `useHasPermission("rooms.manage")` يقرأ قائمة الصلاحيات المرجعة من endpoint `/api/v1/auth/my-hotels/`.
   - إضافة مكون `ProtectedRoute` ومكون `FeatureGuard` لتمرير الشاشات حسب صلاحيات المستخدم.
