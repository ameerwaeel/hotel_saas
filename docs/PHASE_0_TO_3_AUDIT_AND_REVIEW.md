# 🏛️ التقرير المعماري الشامل والتدقيق الفني: من المرحلة 0 إلى المرحلة 3
## HOTEL SaaS Architecture, Post-Phase 3 Audit, and Technical Q&A Guide

**المسار:** `docs/PHASE_0_TO_3_AUDIT_AND_REVIEW.md`  
**التاريخ:** أكتوبر 2026  
**المرجع الأساسي للتخطيط:** `HOTEL_SaaS_Full_Plan (2).md`  
**حالة الاختبارات البرمجية:** 38/38 اختبار ناجح بنسبة 100% (`tests/`)  

---

## 📑 فهرس محتويات الدليل

1. [مقدمة وسجل التعديلات المضافة بعد تنفيذ Phase 3](#1-سجل-التعديلات-والإضافات-التي-تمت-بعد-المرحلة-3)
2. [تدقيق اكتمال عمليات الـ CRUD لكافة الـ Endpoints](#2-تدقيق-اكتمال-عمليات-الـ-crud-لكافة-الـ-endpoints)
3. [كيف يتعرف الموظف/العضو على دوره وفندقه وصلاحياته، وحماية النظام](#3-كيف-يتعرف-الموظف-على-دوره-وفندقه-وصلاحياته-وحماية-النظام)
4. [معمارية نظام الصلاحيات المخصص (RBAC) مقابل Django Groups](#4-معمارية-نظام-الصلاحيات-المخصص-rbac-مقابل-django-groups)
5. [حقول إعدادات الفندق HotelSettings وجدول تفعيلها ونظام العملات المتعددة](#5-حقول-إعدادات-الفندق-hotelsettings-وجدول-تفعيلها-ونظام-العملات-المتعددة)
6. [دورة حياة الـ Access Token والـ Refresh Token وطريقة تجديده](#6-دورة-حياة-الـ-access-token-والـ-refresh-token-وطريقة-تجديده)
7. [هيكل الـ JSON لربط المستخدمين بالفنادق والأدوار في /me/ و /my-hotels/](#7-هيكل-الـ-json-لربط-المستخدمين-بالفنادق-والأدوار)
8. [تكامل البريد الإلكتروني الحقيقي عبر Gmail SMTP ومهام Celery الخلفية](#8-تكامل-البريد-الإلكتروني-الحقيقي-عبر-gmail-smtp-ومهام-celery-الخلفية)
9. [المسميات الوظيفية: التمييز المعماري بين دور الصلاحيات Role والملف الوظيفي Employee](#9-المسميات-الوظيفية-التمييز-المعماري-بين-role-و-employee)
10. [طبقات الأمان الدفاعية المترادفة (Defense-in-Depth Security Layers)](#10-طبقات-الأمان-الدفاعية-المترادفة-defense-in-depth-security-layers)
11. [سيناريو إنشاء فندق بدون مستخدم وربطه بالموظفين لاحقاً](#11-سيناريو-إنشاء-فندق-بدون-مستخدم-وربطه-بالموظفين-لاحقاً)
12. [معمارية إدارة الفروع والسلاسل الفندقية (Multi-Branch Architecture)](#12-معمارية-إدارة-الفروع-والسلاسل-الفندقية-multi-branch-architecture)
13. [نظام تفعيل وتعطيل الميزات المخصصة لكل فندق (Feature Flags)](#13-نظام-تفعيل-وتعطيل-الميزات-المخصصة-لكل-فندق-feature-flags)

---

## 1. سجل التعديلات والإضافات التي تمت بعد المرحلة 3

تنفيذاً للطلب الدقيق للمستخدم بمطابقة المعمارية وتوثيق كل ما تم تطويره: تم رصد وتسجيل كافة التحسينات والإضافات المعمارية التي استجدت بعد تسليم المرحلة 3، لضمان استقرار وجاهزية المنصة:

1. **إضافة مدير المستخدمين المخصص `UserManager(BaseUserManager)`:**
   - *الملف:* `accounts/models.py`
   - *الهدف:* توفير دوال ذرية قياسية `create_user` و `create_superuser` لتوليد المستخدمين من سطر الأوامر أو عبر الـ API بدون الحاجة إلى إدخال حقول غير ضرورية، مع معالجة حقل `phone` الفريد والسماح بقيم `None`.

2. **التوليد التلقائي لإعدادات الفندق (`HotelSettings Signal`):**
   - *الملف:* `tenants/signals.py` و `tenants/apps.py`
   - *الهدف:* عند إنشاء أي فندق جديد في قاعدة البيانات (`Hotel.objects.create`)، يتم إنشاء سجل `HotelSettings` افتراضي فوراً عبر `post_save`، مما يمنع حدوث أخطاء `RelatedObjectDoesNotExist` عند طلب العملة أو المنطقة الزمنية.

3. **دعم تمرير الفندق النشط عبر ترويسة الطلب (`X-Hotel-ID Header`):**
   - *الملف:* `common/middleware/tenant.py`
   - *الهدف:* تمكين تطبيقات الـ Frontend والـ Mobile والـ Postman من تحديد سياق الفندق مباشرة بإرسال `X-Hotel-ID: <UUID>` إلى جانب خيار الجلسة `session['active_hotel_id']`.

4. **توسيع واستحداث نقاط نهاية جديدة في `accounts/`:**
   - `POST /api/v1/auth/register/`: لتسجيل مستخدم جديد عادي.
   - `POST /api/v1/auth/register-hotel/`: لتسجيل فندق جديد بالكامل مع المالك ودور `Owner` وعضوية مفعلة في معاملة ذرية واحدة (`transaction.atomic`).
   - `GET & POST /api/v1/auth/members/`: استعراض وإضافة موظفين وأعضاء للفندق النشط مع إرسال بريد ترحيبي تلقائياً.
   - `/api/v1/auth/users/` (`UserManagementViewSet`): إدارة كاملة لمستخدمي المنصة مخصصة لمدراء المنصة (`IsPlatformAdmin`).
   - `POST /api/v1/auth/reset-password/` & `POST /api/v1/auth/reset-password-confirm/`: دورة متكاملة لطلب وتأكيد استعادة كلمة المرور عبر البريد الإلكتروني.

5. **تجهيز بيئة الاختبار المعزولة `config/settings/testing.py`:**
   - *الهدف:* تعطيل أدوات الـ HTML Profiling (`debug_toolbar`, `silk`) أثناء تشغيل الـ Automated Tests واستخدام SQLite in-memory مع كاش و بريد في الذاكرة `locmem` لضمان سرعة فائقة في الفحص (تنفيذ جميع الاختبارات في أقل من ثانيتين).

6. **إصلاح تصادم حقول التسجيل (`Logging Record Collision Bug`):**
   - *الهدف:* تعديل مفتاح `created` إلى `is_created` في ملفات التسجيل `logger.info(..., extra={...})` لمنع التعارض مع حقل `created` الداخلي في مكتبة `logging` القياسية لبايثون.

---

## 2. تدقيق اكتمال عمليات الـ CRUD لكافة الـ Endpoints

تمت مراجعة جميع نقاط النهاية المتاحة للتأكد من منطق الـ CRUD (إنشاء Create، قراءة Read، تعديل Update، حذف Delete):

| الـ Endpoint | الأفعال المتاحة (HTTP Methods) | هل تم استيفاء الـ CRUD؟ | الملاحظات الفنية والتبرير |
| :--- | :--- | :--- | :--- |
| `/api/v1/tenants/hotels/` | `GET`, `POST` | ✅ كاملة عبر الـ ViewSet | استعراض الفنادق وإنشاء فندق جديد. |
| `/api/v1/tenants/hotels/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | ✅ كاملة عبر الـ ViewSet | قراءة فندق، تعديل كلي، تعديل جزئي، وحذف منطقي أو فعلي. |
| `/api/v1/auth/users/` | `GET`, `POST` | ✅ كاملة عبر الـ ViewSet | قائمة المستخدمين وإنشاء مستخدم (لإدارة المنصة). |
| `/api/v1/auth/users/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | ✅ كاملة عبر الـ ViewSet | إدارة مستخدم محدد (تعديل صلاحيات، حظر، حذف). |
| `/api/v1/auth/members/` | `GET`, `POST` | ✅ مستوفاة للمرحلة | `GET` لاستعراض أعضاء الفندق النشط، `POST` لإضافة/دعوة عضو جديد. حذف وتعديل العضوية محكوم بـ Membership Service في المراحل القادمة. |
| `/api/v1/auth/me/` | `GET`, `PATCH` | ✅ مكتملة منطقياً | الملف الشخصي للمستخدم: قراءة بياناته (`GET`) وتحديثها (`PATCH`). الحذف يتم عبر إيقاف الحساب من قبل الأدمن. |
| `/api/v1/auth/register-hotel/` | `POST` | ✅ عملية أحادية (Action) | نقطة تسجيل Onboarding متخصصة، لا تحتاج إلى GET/DELETE لأن العمليات اللاحقة تتم عبر `/tenants/hotels/`. |
| `/api/v1/auth/login/`, `logout/` | `POST` | ✅ عمليات حالة (State Actions) | تسجيل الدخول وتوليد التوكنات، أو إبطالها وإضافتها للـ Blacklist. |
| `/api/v1/auth/reset-password*` | `POST` | ✅ عمليات مصادقة | طلب كود الاسترجاع وتأكيد كلمة المرور الجديدة. |

---

## 3. كيف يتعرف الموظف على دوره وفندقه وصلاحياته، وحماية النظام

### أ) آلية تدفق البيانات في الواجهة الأمامية و الـ API
لا يحتاج الموظف أو المستخدم لتخمين فندقه أو دوره، فالنظام يوفر دورة عمل واضحة:

```mermaid
sequenceDiagram
    autonumber
    actor User as الموظف / المستخدم
    participant Client as تطبيق Frontend / Mobile
    participant API as خادم HOTEL SaaS
    participant DB as قاعدة البيانات / الكاش

    User->>Client: تسجيل الدخول (Email + Password)
    Client->>API: POST /api/v1/auth/login/
    API-->>Client: 200 OK (Access Token + Refresh Token + User Data)
    
    Client->>API: GET /api/v1/auth/my-hotels/ (مع Access Token)
    API->>DB: استعلام العضويات النشطة مع الأدوار والصلاحيات
    DB-->>API: الفنادق، الأدوار، مصفوفة الصلاحيات
    API-->>Client: قائمة الفنادق (مع hotel_id، hotel_name، role، permission_codes)

    User->>Client: اختيار الفندق للعمل عليه
    Client->>API: POST /api/v1/auth/select-hotel/ {hotel_id: "..."}
    API-->>Client: 200 OK (تم تثبيت الفندق النشط في الجلسة)

    Note over Client,API: أو تمرير Header: X-Hotel-ID: <UUID> في كل طلب
    
    Client->>API: GET /api/v1/auth/me/
    API-->>Client: بيانات المستخدم + الفندق النشط + الدور الحالي + الصلاحيات
```

### ب) حماية النظام من الاختراق وانتحال الأدوار
1. **عزل المستأجر الصارم (`Tenant Isolation`):**  
   حتى لو عرف موظف في "فندق أ" معرف UUID لفندق آخر "فندق ب" وأرسله في ترويسة `X-Hotel-ID` أو في طلب `select-hotel`، فإن `TenantMiddleware` و `IsHotelMember` يعترضان الطلب:
   ```python
   # فحص العضوية في الفندق المطلوب
   membership = HotelMembership.objects.filter(
       user=request.user, hotel=target_hotel, status="active"
   ).exists()
   if not membership and not (request.user.is_platform_admin or request.user.is_superuser):
       return 403 Forbidden ("You are not an active member of this hotel.")
   ```
2. **التحقق من الصلاحيات اللحظي عبر الكاش (`O(1)` Permission Check):**  
   عند تنفيذ أي عملية داخل الفندق (مثل إضافة غرفة أو حجز)، يفحص كلاس `HasHotelPermission("rooms.create")` الصلاحية المسجلة لهذا المستخدم في هذا الفندق المحدد. لا يمكن لموظف استقبال في فندق أن ينفذ مهام محاسبية ما لم يتضمن دوره صلاحية `payments.create`.

---

## 4. معمارية نظام الصلاحيات المخصص (RBAC) مقابل Django Groups

### لماذا تم بناء نظام RBAC مخصص بدلاً من `django.contrib.auth.models.Group`؟
1. **القصور المعماري لـ Django Groups الافتراضية:**  
   مجموعات جانغو الافتراضية هي كيانات عامة مسطحة (Flat & Global) على مستوى النظام ككل ولا ترتبط بأي فندق (`hotel_id`).  
   لو استخدمنا `Group`، فإن إنشاء دور "Receptionist" سيعني أن جميع الفنادق تتشارك نفس الدور؛ وإذا قام مدير فندق بتعديل صلاحيات الدور فإنه سيغيره على جميع فنادق المنصة، وهذا خرق فاضح لمبدأ الـ Multi-Tenancy!
2. **مزايا نموذجنا المخصص:**
   - جدول `Role` يملك حقلاً خارجياً `hotel = ForeignKey(Hotel, on_delete=CASCADE)`.
   - يمكن لكل فندق تعديل مسميات أدواره وصلاحياته بحرية واستقلالية كاملة.
   - الأدوار الافتراضية (`Owner`, `Manager`, `Receptionist`, `Accountant`, `Housekeeping`) تُنشأ آلياً لكل فندق جديد وتُعزل عنه تماماً.
3. **تنسيق كود الصلاحية الموحد (`module.action`):**
   - تم اعتماد نمط `[اسم الموديول].[الفعل]` لجميع الصلاحيات البرمجية:
     - `rooms.view`, `rooms.create`, `rooms.update`, `rooms.delete`
     - `reservations.view`, `reservations.create`, `reservations.checkin`, `reservations.cancel`
     - `payments.view`, `payments.create`, `payments.refund`
     - `customers.view`, `customers.create`
   - يتم تخزين قائمة الأكواد في كاش الذاكرة/Redis تحت المفتاح `perms:{user_id}:{hotel_id}` لتفادي استعلامات قاعدة البيانات المتكررة عند كل طلب HTTP.

---

## 5. حقول إعدادات الفندق HotelSettings وجدول تفعيلها ونظام العملات المتعددة

### أ) تفصيل حقول جدول `HotelSettings`:
- `hotel`: علاقة One-to-One فريدة مع الفندق.
- `currency`: كود العملة الأساسية (ISO 4217) مثل `USD`, `EGP`, `SAR`, `EUR`. تُستخدم كعملة الحسابات والتقارير المالية الأساسية للفندق.
- `timezone`: المنطقة الزمنية للمنشأة (مثل `Africa/Cairo` أو `Asia/Riyadh`) لضبط توقيت تسجيل الوصول والترحيل اليومي للغرف (Night Audit).
- `checkin_time` (افتراضياً `14:00`): وقت بدء تسجيل الوصول القياسي.
- `checkout_time` (افتراضياً `12:00`): وقت المغادرة القياسي (يُبنى عليه جدول مهام الإشراف الداخلي وتنظيف الغرف).
- `cancellation_grace_hours` (افتراضياً `24`): مهلة الإلغاء المجاني بالساعات قبل موعد الوصول.
- `allow_overbooking` (افتراضياً `False`): السماح بحجز غرف تتجاوز السعة الفعلية لتعويض حالات عدم الحضور (No-Shows).
- `tax_percentage` (افتراضياً `14.00%`): نسبة ضريبة القيمة المضافة المحسوبة آلياً في الفواتير.
- `is_multi_currency_enabled` (افتراضياً `False`): تمكين الفندق من تحصيل المدفوعات بعملات أجنبية متعددة.

### ب) الجدول الزمني لتفعيل حقول `HotelSettings` عبر مراحل الخطة (Phases 1-12):
```mermaid
flowchart TD
    P2["المرحلة 2 (Tenants Core)<br/>إنشاء الموديل والربط التلقائي عبر Signals"] --> P4["المرحلة 4 (Rooms & Housekeeping)<br/>تفعيل checkout_time لتوليد مهام التنظيف آلياً"]
    P4 --> P5["المرحلة 5 (Reservations & Booking)<br/>تطبيق checkin_time, grace_hours, allow_overbooking"]
    P5 --> P6["المرحلة 6 (Finance & Multi-Currency)<br/>تفعيل currency, tax_percentage, is_multi_currency"]
    P6 --> P8["المرحلة 8 (Celery & Night Audit)<br/>استخدام timezone لجدولة التقارير التلقائية منتصف الليل"]
    P8 --> P9["المرحلة 9 (Multi-Branch & SaaS Features)<br/>تخصيص إعدادات فرعية على مستوى الفروع"]
```

### ج) معمارية العملات المتعددة في الفنادق (Multi-Currency Architecture):
يدعم النظام نمطين ماليين متقدمين:
1. **نمط التجميع المنفصل للعملات (Split Multi-Currency Sum):**
   - المعاملات لا يتم تحويلها قسرياً عند الدفع، بل تُسجل كل دفعة بعملتها الأصلية (مثال: دفع العميل 100 دولار و 500 جنيه مصري).
   - عند عرض الإيرادات، يقدم النظام مجاميع منفصلة لكل عملة (`Total: 100 USD + 500 EGP`)، وهو النمط الأمثل لمنع خسائر تقلبات الصرف.
2. **نمط التحويل الموحد بأسعار الصرف (Unified Currency Conversion):**
   - يتم عبر جدول `ExchangeRate(hotel, base_currency, target_currency, rate, date)` الذي سنضيفه في المرحلة 6.
   - يسمح بتحويل إجمالي الإيرادات إلى العملة الأساسية للفندق لغايات الضرائب والقوائم المالية الموحدة.

---

## 6. دورة حياة الـ Access Token والـ Refresh Token وطريقة تجديده

### أ) لماذا نستخدم نوعين من التوكنات؟
- **Access Token:** مدة صلاحيته قصيرة (مثلاً 60 دقيقة). يُرسل في ترويسة الطلب:
  ```http
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6...
  ```
  هذا التوكن محمي ومشفر وغير مخزن في قاعدة البيانات لتسريع التحقق (Stateless JWT). في حال تسريبه ينتهي أثره سريعاً.
- **Refresh Token:** مدة صلاحيته طويلة (مثلاً 7 إلى 30 يوماً). لا يُستخدم في طلبات الـ API العادية، بل يُستخدم في نقطة نهاية واحدة فقط لتجديد الـ Access Token عند انتهائه.

### ب) كيفية تجديد الـ Access Token المنتهي:
عندما تنتهي مدة الـ Access Token، يُرجع الخادم خطأ `401 Unauthorized` بكود `token_not_valid`. يقوم تطبيق الواجهة الأمامية فوراً وبشكل غير مرئي للمستخدم بالطلب التالي:
- **URL:** `POST /api/v1/auth/token/refresh/`
- **Body:**
  ```json
  {
    "refresh": "<your_refresh_token_here>"
  }
  ```
- **Response:**
  ```json
  {
    "access": "<new_fresh_access_token>"
  }
  ```
يقوم التطبيق بتحديث التوكن وإعادة إرسال الطلب الأصلي دون أن يشعر المستخدم بأي انقطاع أو يُطالب بإعادة إدخال كلمة المرور.

### ج) سبب الخطأ السابق في تسجيل الخروج `/logout/`:
تسجيل الخروج في نظامنا يتبع أفضل ممارسات الأمان بإلغاء التوكن نهائياً (`Blacklisting`). لذلك يتطلب إرسال الـ `refresh` token في الطلب:
```json
// POST /api/v1/auth/logout/
{
  "refresh": "<refresh_token>"
}
```
بهذا الإجراء يُحظر الـ Refresh Token تماماً في قاعدة البيانات لمنع إعادة استخدامه.

---

## 7. هيكل الـ JSON لربط المستخدمين بالفنادق والأدوار

### أ) استعلام بيانات المستخدم الحالي مع الفندق النشط:
- **Endpoint:** `GET /api/v1/auth/me/`
- **Headers:** `Authorization: Bearer <token>`, `X-Hotel-ID: <active_hotel_id>`
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "id": "2f1b3eb4-6765-4936-9341-9434b473e7ea",
    "email": "karim.hassan@cairopalace.com",
    "username": "karim.hassan",
    "first_name": "Karim",
    "last_name": "Hassan",
    "full_name": "Karim Hassan",
    "phone": "+201099887766",
    "avatar": null,
    "preferred_language": "ar",
    "is_platform_admin": false,
    "date_joined": "2026-10-01T10:15:30Z",
    "last_login": "2026-10-01T15:20:00Z",
    "active_hotel": {
      "id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
      "name": "Cairo Palace Hotel",
      "subdomain": "cairo-palace"
    },
    "current_role": "Owner",
    "permissions": [
      "rooms.view",
      "rooms.create",
      "rooms.update",
      "rooms.delete",
      "reservations.view",
      "reservations.create",
      "payments.view",
      "customers.view"
    ]
  }
}
```

### ب) استعلام قائمة الفنادق التي ينتمي إليها المستخدم:
- **Endpoint:** `GET /api/v1/auth/my-hotels/`
- **Headers:** `Authorization: Bearer <token>`
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "9a1b2c3d-4e5f-6789-0abc-def123456789",
      "hotel_id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
      "hotel_name": "Cairo Palace Hotel",
      "hotel_subdomain": "cairo-palace",
      "role": {
        "id": "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "Owner",
        "description": "Full access to hotel operations",
        "is_system_role": true,
        "permissions": [
          {"code": "rooms.view", "name": "View Rooms"},
          {"code": "rooms.create", "name": "Create Rooms"}
        ],
        "members_count": 1,
        "created_at": "2026-10-01T10:00:00Z"
      },
      "status": "active",
      "joined_at": "2026-10-01T10:15:30Z",
      "permission_codes": [
        "rooms.view",
        "rooms.create",
        "reservations.view",
        "payments.view"
      ]
    }
  ]
}
```

---

## 8. تكامل البريد الإلكتروني الحقيقي عبر Gmail SMTP ومهام Celery الخلفية

### أ) إعدادات SMTP المؤكدة والمفعلة في `.env`:
تم ربط الحساب واختبار الاتصال والمصادقة بنجاح بنسبة 100%:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ameer.waeel99@gmail.com
EMAIL_HOST_PASSWORD=kdgyplbphzfasbpf
DEFAULT_FROM_EMAIL=HOTEL SaaS <ameer.waeel99@gmail.com>
```

### ب) معمارية الإرسال المرن (`accounts/tasks.py`):
تم بناء دالة `send_mail_resilient` الذكية:
1. تحاول إرسال البريد عبر Celery Worker غير المتزامن (`send_async_email.delay`).
2. في حال كان خادم Redis غير مشغل محلياً أثناء التطوير، لا يتعطل النظام أبداً بل يتم تفعيل الـ Fallback التلقائي للإرسال المتزامن المباشر، مما يمنع انقطاع خدمة المستخدمين.

### ج) دورة استعادة كلمة المرور الكاملة (Password Reset Flow):
1. **طلب استعادة كلمة المرور:**  
   - **URL:** `POST /api/v1/auth/reset-password/`
   - **Body:** `{"email": "user@example.com"}`
   - **النتيجة:** يولد النظام رمزاً آمناً مؤقتاً (`default_token_generator`) ومعرف مستخدم مشفر (`uid`) ويتم إرسالهما في رسالة بريد إلكتروني منسقة إلى بريد العميل.
2. **تأكيد كلمة المرور الجديدة:**  
   - **URL:** `POST /api/v1/auth/reset-password-confirm/`
   - **Body:**
     ```json
     {
       "uid": "<base64_encoded_user_id>",
       "token": "<reset_token>",
       "new_password": "NewSecurePassword123!",
       "confirm_password": "NewSecurePassword123!"
     }
     ```
   - **النتيجة:** يتم فك تشفير المعرف، والتحقق من صحة وصلاحية الـ Token، وتحديث كلمة المرور في قاعدة البيانات.

---

## 9. المسميات الوظيفية: التمييز المعماري بين Role و Employee

سأل المستخدم عن كيفية إدارة المسميات الوظيفية (مثل محاسب، موظف استقبال، مدير، مشرف صيانة):

```
                        ┌─────────────────────────────────────────────────┐
                        │             الأمان الرقمي والتحكم                │
                        │                    Role                         │
                        │       (accounts.models.Role)                    │
                        │  - permissions: ['rooms.view', 'rooms.edit']    │
                        │  - hotel: Hotel A                               │
                        └──────────────────────▲──────────────────────────┘
                                               │ يرتبط بـ
                                               │
┌──────────────────────────────┐        ┌──────┴──────────────────────────┐
│        المصادقة والتسجيل     │        │        الهيكل الوظيفي الإداري    │
│             User             │◄───────┤              Employee           │
│    (accounts.models.User)    │        │         (Phase 4: rooms/hr)     │
│  - email: mona@hotel.com     │        │  - job_title: "Senior Desk Clerk│
│  - password: hashed          │        │  - department: "Front Office"   │
│  - is_active: True           │        │  - shift: "Morning (08:00-16:00)│
│                              │        │  - hire_date: 2026-01-01        │
│                              │        │  - national_id: "2990101..."    │
└──────────────────────────────┘        └─────────────────────────────────┘
```

1. **كائن الدور (`Role` - Phase 3):**  
   هو كيان تقني أمني بحت. وظيفته تحديد: "ما الذي يستطيع هذا الحساب رؤيته أو التعديل عليه في الـ API وقاعدة البيانات؟".
2. **كائن الموظف (`Employee` - Phase 4):**  
   هو كيان إداري وتنظيمي. وظيفته إدارة الموارد البشرية (القسم، المسمى الوظيفي الدقيق، الراتب، مواعيد الورديات، والمهام اليومية المسندة إليه).

---

## 10. طبقات الأمان الدفاعية المترادفة (Defense-in-Depth Security Layers)

كل طلب HTTP وارد إلى منصة HOTEL SaaS يعبر عبر 6 بوابات أمان متتالية:

```
[1. HTTP Request] ──► [2. JWT Authentication] ──► [3. Tenant Middleware]
                                                            │
    ┌───────────────────────────────────────────────────────┘
    ▼
[4. Platform Admin Bypass / Hotel Membership Verification]
    │
    ▼
[5. Role-Based Permissions (HasHotelPermission via Redis)]
    │
    ▼
[6. Database Isolation (TenantQuerySet.for_hotel)] ──► [Data Returned]
```

1. **الطبقة 1: التحقق من الهوية (JWT Authentication):** فحص صلاحية التوكن وتوقيعه الرقمي واستخراج المستخدم.
2. **الطبقة 2: عزل الفندق (`TenantMiddleware`):** قراءة `X-Hotel-ID` أو `session` وحقن كائن الفندق في `request.hotel` بعد التأكد من أنه فندق نشط وعامل (`is_operational`).
3. **الطبقة 3: فحص صلاحيات المنصة (`IsPlatformAdmin`):** التأكد مما إذا كان المستخدم يملك صلاحية إدارة الساس بأكملها.
4. **الطبقة 4: فحص عضوية الفندق (`IsHotelMember`):** منع أي مستخدم لا يملك سجلاً نشطاً في `HotelMembership` من دخول الفندق.
5. **الطبقة 5: فحص الصلاحية الدقيقة (`HasHotelPermission`):** التحقق من احتواء دور المستخدم على كود الصلاحية المطلوب للعملية المحددة.
6. **الطبقة 6: عزل قاعدة البيانات الصارم (`TenantQuerySet`):** تصفية كافة استعلامات الـ ORM تلقائياً بـ `.filter(hotel=request.hotel)` لضمان استحالة تسرب أي سجل بين الفنادق حتى لو حدث خطأ برمجي في الطبقات السابقة.

---

## 11. سيناريو إنشاء فندق بدون مستخدم وربطه بالموظفين لاحقاً

يدعم النظام هذا السيناريو بنسبة 100%:
1. **إنشاء الفندق مجرداً بواسطة مدير المنصة:**
   - **URL:** `POST /api/v1/tenants/hotels/`
   - **Headers:** `Authorization: Bearer <platform_admin_token>`
   - **Body:**
     ```json
     {
       "name": "Alexandria Sea Hotel",
       "subdomain": "alex-sea",
       "email": "contact@alexsea.com",
       "phone": "+2033445566",
       "city": "Alexandria",
       "country": "EG"
     }
     ```
   - ينشأ الفندق مع إعداداته التلقائية `HotelSettings` وتكون قائمته خالية من الأعضاء.
2. **ربط المالك أو الموظفين لاحقاً:**
   - يختار الأدمن أو المشرف الفندق عبر `X-Hotel-ID`.
   - يرسل طلب إضافة موظف:
     - **URL:** `POST /api/v1/auth/members/`
     - **Body:**
       ```json
       {
         "email": "manager@alexsea.com",
         "role_id": "<role_uuid>",
         "first_name": "Tamer",
         "last_name": "Hosny"
       }
       ```
   - ينشئ النظام المستخدم ويربطه بالفندق في سجل `HotelMembership` ويرسل له بريداً ترحيبياً بكلمة المرور المؤقتة.

---

## 12. معمارية إدارة الفروع والسلاسل الفندقية (Multi-Branch Architecture)

لإدارة الفنادق التي تمتلك فروعاً متعددة (مثل سلسلة فنادق تمتلك فرعاً في القاهرة وفرعاً في الغردقة وترغب في لوحة تحكم مركزية):
- يتم دعم ذلك معمارياً في المرحلة 2 و 9 بإضافة حقل تكراري ذاتي في موديل `Hotel`:
  ```python
  parent = models.ForeignKey(
      'self',
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='branches',
      help_text="الفندق الرئيسي أو السلسلة الأم"
  )
  ```
- **المزايا المعمارية:**
  - كل فرع يملك `hotel_id` وإعدادات وغرف وحجوزات معزولة بالكامل عن الفرع الآخر لضمان خصوصية العمليات اليومية.
  - يستطيع مدير السلسلة العام الاستعلام عن كافة الفروع التابعة:
    ```python
    branch_ids = hotel.branches.values_list('id', flat=True)
    all_reservations = Reservation.objects.filter(hotel_id__in=[hotel.id, *branch_ids])
    ```

---

## 13. نظام تفعيل وتعطيل الميزات المخصصة لكل فندق (Feature Flags)

للسماح باشتراكات متفاوتة (باقة أساسية Basic، باقة متقدمة Pro، باقة كبرى Enterprise):
1. **جدول الميزات (`Feature` و `HotelFeature`):**
   - ميزات مثل: `channel_manager` (الربط مع Booking.com)، `housekeeping_live_chat`، `accounting_export`، `multi_currency`.
2. **التحقق البرمجي على مستوى الـ API:**
   - يتم حماية الـ Endpoint بكلاس حماية مخصص:
     ```python
     class RequiresFeature(BasePermission):
         def __init__(self, feature_code):
             self.feature_code = feature_code
             
         def has_permission(self, request, view):
             return request.hotel.has_feature(self.feature_code)
     ```
   - إذا حاول فندق مشترك في الباقة الأساسية استخدام ميزة الـ Channel Manager، يُرد عليه بـ `403 Forbidden` برسالة واضحة: `Feature not enabled for your subscription plan`.

---

## 14. ملخص نتائج الاختبارات وضمان الجودة

تم تشغيل حزمة الاختبارات الشاملة للمشروع بنجاح:
```bash
$ pytest tests/ -v
============================= test session starts =============================
collected 38 items

tests/test_auth.py::TestLogin::test_login_success PASSED                 [  2%]
tests/test_auth.py::TestLogin::test_login_wrong_password PASSED          [  5%]
tests/test_auth.py::TestLogin::test_login_wrong_email PASSED             [  7%]
tests/test_auth.py::TestLogin::test_login_missing_fields PASSED          [ 10%]
tests/test_auth.py::TestLogout::test_logout_success PASSED               [ 13%]
tests/test_auth.py::TestLogout::test_logout_without_auth PASSED          [ 15%]
tests/test_auth.py::Test401vs403Distinction::test_unauthenticated_request_returns_401 PASSED [ 18%]
tests/test_auth.py::Test401vs403Distinction::test_authenticated_without_hotel_access_returns_403 PASSED [ 21%]
tests/test_auth.py::Test401vs403Distinction::test_platform_admin_can_access_hotels PASSED [ 23%]
tests/test_auth.py::TestMeEndpoint::test_get_me PASSED                   [ 26%]
tests/test_auth.py::TestMeEndpoint::test_update_me PASSED                [ 28%]
tests/test_auth.py::TestMeEndpoint::test_get_me_with_active_hotel PASSED [ 31%]
tests/test_auth.py::TestSelectHotel::test_select_valid_hotel PASSED      [ 34%]
tests/test_auth.py::TestSelectHotel::test_select_hotel_not_member PASSED [ 36%]
tests/test_auth.py::TestSelectHotel::test_select_hotel_platform_admin_can_select_any_hotel PASSED [ 39%]
tests/test_auth.py::TestMyHotels::test_my_hotels_with_membership PASSED  [ 42%]
tests/test_auth.py::TestMyHotels::test_my_hotels_empty PASSED            [ 44%]
tests/test_auth.py::TestPermissionCaching::test_permissions_are_cached PASSED [ 47%]
tests/test_auth.py::TestPermissionCaching::test_cache_invalidated_on_role_change PASSED [ 50%]
tests/test_registration.py::TestUserRegistration::test_register_user_success PASSED [ 52%]
tests/test_registration.py::TestUserRegistration::test_register_duplicate_email PASSED [ 55%]
tests/test_registration.py::TestHotelRegistrationOnboarding::test_register_hotel_with_owner_success PASSED [ 57%]
tests/test_registration.py::TestHotelRegistrationOnboarding::test_register_hotel_duplicate_subdomain PASSED [ 60%]
tests/test_registration.py::TestHotelMemberAddition::test_add_member_to_hotel_success PASSED [ 63%]
tests/test_registration.py::TestPlatformAdminUserManagement::test_admin_create_platform_admin PASSED [ 65%]
tests/test_registration.py::TestHotelMemberList::test_list_members_success PASSED [ 68%]
tests/test_registration.py::TestPasswordResetFlow::test_password_reset_request_and_confirm_flow PASSED [ 71%]
tests/test_tenant_isolation.py::TestTenantQuerySetIsolation::test_for_hotel_returns_only_hotel_a_roles PASSED [ 73%]
tests/test_tenant_isolation.py::TestTenantQuerySetIsolation::test_tenant_manager_for_hotel_none_returns_empty PASSED [ 76%]
tests/test_tenant_isolation.py::TestTenantQuerySetIsolation::test_membership_scoped_to_hotel PASSED [ 78%]
tests/test_tenant_isolation.py::TestSelectHotelIsolation::test_cannot_select_hotel_without_membership PASSED [ 81%]
tests/test_tenant_isolation.py::TestSelectHotelIsolation::test_can_select_hotel_with_membership PASSED [ 84%]
tests/test_tenant_isolation.py::TestPermissionCrossHotelIsolation::test_permissions_scoped_to_hotel PASSED [ 86%]
tests/test_tenant_isolation.py::TestPermissionCrossHotelIsolation::test_platform_admin_bypasses_tenant_isolation PASSED [ 89%]
tests/test_tenant_isolation.py::TestHotelModel::test_hotel_is_operational PASSED [ 92%]
tests/test_tenant_isolation.py::TestHotelModel::test_inactive_hotel_not_operational PASSED [ 94%]
tests/test_tenant_isolation.py::TestHotelModel::test_suspended_hotel_not_operational PASSED [ 97%]
tests/test_tenant_isolation.py::TestHotelModel::test_hotel_str_representation PASSED [100%]

============================= 38 passed in 1.44s ==============================
```

كل متطلبات المراحل 0 و 1 و 2 و 3 مكتملة وموثقة وتعمل بأعلى درجات الكفاءة والأمان.
