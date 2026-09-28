# 🟦 Phase 3 — Authentication + RBAC + Hotel Membership (المصادقة والأدوار والصلاحيات)

المسار في التوثيق: `docs/PHASE_3_DOCS.md`  
الهدف: بناء نظام مصادقة المستخدمين وإدارة الأدوار والصلاحيات المخصصة داخل الفنادق وتخزينها مؤقتاً في الـ Cache لمنع N+1 queries.

---

## 🛠️ الملفات التي تم إنشاؤها وتعديلها في Phase 3

| اسم الملف | المسار المباشر | الوظيفة والتفاصيل |
| :--- | :--- | :--- |
| `accounts/models.py` | [models.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/models.py) | يحتوي على النماذج: `User`, `HotelMembership`, `Role`, `Permission`, `RolePermission` |
| `common/permissions/hotel_permissions.py` | [hotel_permissions.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/common/permissions/hotel_permissions.py) | فئات الصلاحيات: `IsHotelMember`, `HasHotelPermission(code)`, `IsPlatformAdmin` والدالة `get_user_permissions_for_hotel` مع Caching |
| `accounts/signals.py` | [signals.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/signals.py) | إشارات Django لمسح الـ Permission Cache فوراً عند تغيير الأدوار أو العضويات |
| `accounts/serializers.py` | [serializers.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/serializers.py) | محولات البيانات الحسابية والصلاحيات وتفادي N+1 في الـ Nested Serializers |
| `accounts/views.py` | [views.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/views.py) | مشاهد التسجيل والدخول وإدارة الجلسات واختيار الفندق النشط |
| `accounts/urls.py` | [urls.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/urls.py) | المسارات البرمجية المركزية الخاصة بـ `/api/v1/auth/` |
| `accounts/admin.py` | [admin.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/accounts/admin.py) | إعدادات لوحة التحكم لمديري المستخدمين والأدوار والصلاحيات |
| `tests/test_auth.py` | [test_auth.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tests/test_auth.py) | حزمة اختبارات المصادقة والصلاحيات (17 اختباراً ناجحاً) |
| `tests/test_tenant_isolation.py` | [test_tenant_isolation.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/tests/test_tenant_isolation.py) | حزمة اختبارات عزل البيانات بين الفنادق (11 اختباراً ناجحاً) |

---

## 🗄️ نماذج قاعدة البيانات (Database Models):

1. **`User` Model (المستخدم المخصص)**:
   - ينوب عن `AbstractUser` ببريد إلكتروني فريد للدخول `USERNAME_FIELD = "email"`.
   - الحقول: `id` (UUID), `email` (مفهرس فريد), `phone`, `avatar`, `is_platform_admin`, `preferred_language`.

2. **`HotelMembership` Model (عضوية الفندق)**:
   - ربط المستخدم بالفندق بـ `Role` محدد.
   - القيود والفهارس:
     - `UniqueConstraint(fields=["user", "hotel"])`
     - فهارس مركبة على `(hotel, status)` و `(user, status)`.

3. **`Role` Model (أدوار الفندق)**:
   - الأدوار المخصصة داخل الفندق الواحد (مثل Manager, Receptionist).
   - القيود: `UniqueConstraint(fields=["hotel", "name"])`.

4. **`Permission` & `RolePermission` Models**:
   - `Permission`: الصلاحيات العامة بالنظام (مثل `rooms.manage`, `finance.view`).
   - `RolePermission`: جدول الربط بين الأدوار والصلاحيات (`UniqueConstraint(role, permission)`).

---

## ⚡ حل مشكلة N+1 والتخزين المؤقت للصلاحيات (Permission Caching):

- يتم استعلام وحساب صلاحيات المستخدم في الفندق وتخزينها في Cache تحت المفتاح `"perms:{user_id}:{hotel_id}"` لمدة 5 دقائق.
- **تفريغ الكاش التلقائي**: عند قيام الأدمن بتغيير دور الموظف أو تعديل الصلاحيات، تقوم الـ Signals في `accounts/signals.py` بإبطال الكاش فوراً ليتم تحديث الصلاحيات في الطلب القادم مباشرة.

---

## 🌐 جدول الـ Endpoints المكتملة في Phase 3:

| الميثود | المسار (Endpoint) | الوظيفة |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login/` | تسجيل الدخول واستلام JWT Access & Refresh Tokens |
| `POST` | `/api/v1/auth/logout/` | إبطال Refresh Token وإضافته للـ Blacklist |
| `POST` | `/api/v1/auth/token/refresh/` | تجديد Access Token |
| `GET` | `/api/v1/auth/me/` | جلب ملف المستخدم الحالي |
| `PATCH`| `/api/v1/auth/me/` | تعديل ملف المستخدم الحالي |
| `POST` | `/api/v1/auth/change-password/` | تغيير كلمة المرور |
| `POST` | `/api/v1/auth/reset-password/` | طلب إعادة تعيين كلمة المرور |
| `POST` | `/api/v1/auth/select-hotel/` | تعيين الفندق النشط للجلسة |
| `GET` | `/api/v1/auth/my-hotels/` | قائمة الفنادق والأدوار والصلاحيات الخاصة بالمستخدم |

---

## 🌐 ملاحظات الفرونت إند (React - Phase 3):
> [!NOTE] أجزاء الفرونت إند المؤجلة لهذه المرحلة:
> - صفحات Login / Logout في React.
> - تخزين الـ Tokens في `localStorage` أو `httpOnly Cookies`.
> - بناء `useAuth()` hook و `useHasPermission("rooms.manage")` hook.
> - إنشاء مكون `ProtectedRoute` لحماية الصفحات من الزوار غير المصرحين.
