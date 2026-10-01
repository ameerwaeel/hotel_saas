# 🌐 دليل جميع الـ Endpoints ونماذج الـ JSON في مشروع HOTEL SaaS

المسار: `docs/endpoints/ALL_ENDPOINTS.md`  
النسخة: `v1.0.0`  
الهدف: توثيق شامل ودقيق لكل نقطة نهاية (API Endpoint) تم بناؤها في المشروع مع شكل الـ JSON الخاص بالطلب (Request) والاستجابة (Response) وحالات الخطأ (Errors).

---

## 📑 فهرس الـ Endpoints

### 1. مصادقة المستخدمين وحسابات الموظفين (`/api/v1/auth/`)
- [1.1 تسجيل الدخول (Login)](#11-تسجيل-الدخول-login)
- [1.2 تسجيل الخروج (Logout)](#12-تسجيل-الخروج-logout)
- [1.3 تجديد Access Token (Token Refresh)](#13-تجديد-access-token-token-refresh)
- [1.4 استرجاع الملف الشخصي الحالي (Get Profile - Me)](#14-استرجاع-الملف-الشخصي-الحالي-get-profile---me)
- [1.5 تعديل الملف الشخصي (Update Profile - Me)](#15-تعديل-الملف-الشخصي-update-profile---me)
- [1.6 تغيير كلمة المرور (Change Password)](#16-تغيير-كلمة-المرور-change-password)
- [1.7 طلب إعادة تعيين كلمة المرور (Password Reset Request)](#17-طلب-إعادة-تعيين-كلمة-المرور-password-reset-request)
- [1.8 اختيار الفندق النشط (Select Active Hotel)](#18-اختيار-الفندق-النشط-select-active-hotel)
- [1.9 استعراض فنادق وأدوار وصلاحيات المستخدم (My Hotels)](#19-استعراض-فنادق-وأدوار-وصلاحيات-المستخدم-my-hotels)

### 2. إدارة الفنادق والمستأجرين (`/api/v1/tenants/`)
- [2.1 استعراض قائمة الفنادق (List Hotels)](#21-استعراض-قائمة-الفنادق-list-hotels)
- [2.2 إنشاء فندق جديد (Create Hotel)](#22-إنشاء-فندق-جديد-create-hotel)
- [2.3 جلب تفاصيل فندق محدد (Retrieve Hotel Detail)](#23-جلب-تفاصيل-فندق-محدد-retrieve-hotel-detail)
- [2.4 تعديل بيانات فندق بالكامل (Update Hotel - PUT)](#24-تعديل-بيانات-فندق-بالكامل-update-hotel---put)
- [2.5 تعديل جزئي لبيانات فندق (Partial Update Hotel - PATCH)](#25-تعديل-جزئي-لبيانات-فندق-partial-update-hotel---patch)
- [2.6 حذف فندق (Delete Hotel)](#26-حذف-فندق-delete-hotel)

### 3. نقاط نهاية النظام والتوثيق والمراقبة (System & Docs)
- [3.1 OpenAPI Schema](#31-openapi-schema)
- [3.2 Swagger UI Documentation](#32-swagger-ui-documentation)
- [3.3 ReDoc Documentation](#33-redoc-documentation)
- [3.4 مراقبة وتتبع الأداء (Silk Profiling)](#34-مراقبة-وتتبع-الأداء-silk-profiling)
- [3.5 شريط فحص استعلامات SQL (Debug Toolbar)](#35-شريط-فحص-استعلامات-sql-debug-toolbar)

### 4. بنية الاستجابات والأخطاء الموحدة (Standard Response Contracts)
- [4.1 هيكل الاستجابة الناجحة القياسية](#41-هيكل-الاستجابة-الناجحة-القياسية)
- [4.2 هيكل التصفحة القياسي الموحد (Pagination)](#42-هيكل-التصفحة-القياسي-الموحد-pagination)
- [4.3 هيكل رسائل الخطأ الموحد (Standard Error Format)](#43-هيكل-رسائل-الخطأ-الموحد-standard-error-format)

---

## 4. بنية الاستجابات والأخطاء الموحدة (Standard Response Contracts)

### 4.1 هيكل الاستجابة الناجحة القياسية
```json
{
  "success": true,
  "data": { ... }
}
```

### 4.2 هيكل التصفحة القياسي الموحد (Pagination)
المصدر: `common/pagination/pagination.py` (`HotelSaaSPagination`)
```json
{
  "success": true,
  "count": 150,
  "total_pages": 8,
  "current_page": 1,
  "page_size": 20,
  "next": "http://127.0.0.1:8000/api/v1/tenants/hotels/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### 4.3 هيكل رسائل الخطأ الموحد (Standard Error Format)
المصدر: `common/exceptions/handlers.py` (`custom_exception_handler`)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "اسم الحقل أو وصف الخطأ العام",
    "details": {
      "email": [
        "Enter a valid email address."
      ]
    },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```
*الأكواد المعتمدة (`error.code`):*
- `VALIDATION_ERROR` (400)
- `AUTHENTICATION_FAILED` (401)
- `PERMISSION_DENIED` (403)
- `NOT_FOUND` (404)
- `METHOD_NOT_ALLOWED` (405)
- `CONFLICT` (409)
- `INTERNAL_SERVER_ERROR` (500)

---

## 1. مصادقة المستخدمين وحسابات الموظفين (`/api/v1/auth/`)

---

### 1.1 تسجيل الدخول (Login)
- **URL:** `/api/v1/auth/login/`
- **Method:** `POST`
- **Auth Required:** لا (Public)
- **Headers:** `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "email": "admin@hotel.com",
  "password": "SecurePassword123!"
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkxMDM1MDUwLCJpYXQiOjE3OTEwMzE0NTAsImp0aSI6IjBhY2RhYzE0MTA4MTRiYzY5NjM0NDU2Yzg2NDQ4Y2NhIiwidXNlcl9pZCI6IjVlM2RkOTQzLTVhMWItNDlmNC1hYjdiLWFiNzZkZjIxMjE2YiJ9.example",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc5MTYzNjI1MCwiaWF0IjoxNzkxMDMxNDUwLCJqdGkiOiJkMmRjMmM2Nzc1YTY0MWZkODhmMjg0MGY2MjY5NzAwZSIsInVzZXJfaWQiOiI1ZTNkZDk0My01YTFiLTQ5ZjQtYWI3Yi1hYjc2ZGYyMTIxNmIifQ.example",
    "user": {
      "id": "5e3dd943-5a1b-49f4-ab7b-ab76df21216b",
      "email": "admin@hotel.com",
      "username": "admin",
      "first_name": "Ameer",
      "last_name": "Waeel",
      "full_name": "Ameer Waeel",
      "phone": "+201000000000",
      "avatar": null,
      "preferred_language": "en",
      "is_platform_admin": false,
      "date_joined": "2026-09-28T16:25:34Z",
      "last_login": "2026-10-01T11:00:00Z"
    }
  }
}
```

#### Error Response (بيانات خاطئة) `401 Unauthorized`:
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid email or password.",
    "details": null,
    "request_id": "c1f7b539-72f5-4dc7-ba91-7f8ddc6ba3d2"
  }
}
```

---

### 1.2 تسجيل الخروج (Logout)
- **URL:** `/api/v1/auth/logout/`
- **Method:** `POST`
- **Auth Required:** نعم (`Bearer <access_token>`)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCI..."
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "message": "Logged out successfully."
}
```

#### Error Response (رمز غير صالح) `400 Bad Request`:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Token is invalid or expired",
    "details": null,
    "request_id": "8c0a37b1-2e1d-4001-8b43-98782a13cc5e"
  }
}
```

---

### 1.3 تجديد Access Token (Token Refresh)
- **URL:** `/api/v1/auth/token/refresh/`
- **Method:** `POST`
- **Auth Required:** لا (Public)
- **Headers:** `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCI..."
}
```

#### Success Response `200 OK`:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access_token_here..."
}
```

---

### 1.4 استرجاع الملف الشخصي الحالي (Get Profile - Me)
- **URL:** `/api/v1/auth/me/`
- **Method:** `GET`
- **Auth Required:** نعم (`Bearer <access_token>`)
- **Headers:** `Authorization: Bearer <access_token>`

#### Request Body: *فارغ*

#### Success Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "id": "5e3dd943-5a1b-49f4-ab7b-ab76df21216b",
    "email": "admin@hotel.com",
    "username": "admin",
    "first_name": "Ameer",
    "last_name": "Waeel",
    "full_name": "Ameer Waeel",
    "phone": "+201000000000",
    "avatar": null,
    "preferred_language": "en",
    "is_platform_admin": false,
    "date_joined": "2026-09-28T16:25:34Z",
    "last_login": "2026-10-01T11:00:00Z"
  }
}
```

#### Error Response (غير مسجل) `401 Unauthorized`:
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Authentication credentials were not provided.",
    "details": null,
    "request_id": "f29b46c8-1090-4e31-8ff6-3245dae659b8"
  }
}
```

---

### 1.5 تعديل الملف الشخصي (Update Profile - Me)
- **URL:** `/api/v1/auth/me/`
- **Method:** `PATCH`
- **Auth Required:** نعم (`Bearer <access_token>`)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "first_name": "Ameer",
  "last_name": "Waeel Updated",
  "phone": "+201122334455",
  "preferred_language": "ar"
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "id": "5e3dd943-5a1b-49f4-ab7b-ab76df21216b",
    "email": "admin@hotel.com",
    "username": "admin",
    "first_name": "Ameer",
    "last_name": "Waeel Updated",
    "full_name": "Ameer Waeel Updated",
    "phone": "+201122334455",
    "avatar": null,
    "preferred_language": "ar",
    "is_platform_admin": false,
    "date_joined": "2026-09-28T16:25:34Z",
    "last_login": "2026-10-01T11:00:00Z"
  }
}
```

---

### 1.6 تغيير كلمة المرور (Change Password)
- **URL:** `/api/v1/auth/change-password/`
- **Method:** `POST`
- **Auth Required:** نعم (`Bearer <access_token>`)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "old_password": "OldPassword123!",
  "new_password": "NewStrongPassword456!",
  "confirm_password": "NewStrongPassword456!"
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "message": "Password changed successfully."
}
```

#### Error Response (عدم تطابق الكلمتين) `400 Bad Request`:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "confirm_password: Passwords do not match.",
    "details": {
      "confirm_password": [
        "Passwords do not match."
      ]
    },
    "request_id": "761d15bf-32a2-4a0b-a63e-324df5cb6a74"
  }
}
```

---

### 1.7 طلب إعادة تعيين كلمة المرور (Password Reset Request)
- **URL:** `/api/v1/auth/reset-password/`
- **Method:** `POST`
- **Auth Required:** لا (Public)
- **Headers:** `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "email": "admin@hotel.com"
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "message": "If this email exists, a reset link has been sent."
}
```

---

### 1.8 اختيار الفندق النشط (Select Active Hotel)
- **URL:** `/api/v1/auth/select-hotel/`
- **Method:** `POST`
- **Auth Required:** نعم (`Bearer <access_token>`)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "hotel_id": "18c0df1b-31d2-4ef8-a37a-75176b6ef001"
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "hotel_id": "18c0df1b-31d2-4ef8-a37a-75176b6ef001",
    "hotel_name": "Hilton Cairo Heliopolis",
    "hotel_subdomain": "hilton-cairo"
  }
}
```

#### Error Response (المستخدم ليس عضواً في هذا الفندق) `400 Bad Request`:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "hotel_id: You are not an active member of this hotel.",
    "details": {
      "hotel_id": [
        "You are not an active member of this hotel."
      ]
    },
    "request_id": "0d27ce6c-9c98-4c8d-8a90-349f2b1d3d5f"
  }
}
```

---

### 1.9 استعراض فنادق وأدوار وصلاحيات المستخدم (My Hotels)
- **URL:** `/api/v1/auth/my-hotels/`
- **Method:** `GET`
- **Auth Required:** نعم (`Bearer <access_token>`)
- **Headers:** `Authorization: Bearer <access_token>`

#### Request Body: *فارغ*

#### Success Response `200 OK`:
```json
{
  "success": true,
  "data": [
    {
      "id": "7fae0176-7bc2-4523-bd0d-13f5635cb049",
      "user": {
        "id": "5e3dd943-5a1b-49f4-ab7b-ab76df21216b",
        "email": "admin@hotel.com",
        "username": "admin",
        "first_name": "Ameer",
        "last_name": "Waeel",
        "full_name": "Ameer Waeel",
        "phone": "+201000000000",
        "avatar": null,
        "preferred_language": "en",
        "is_platform_admin": false,
        "date_joined": "2026-09-28T16:25:34Z",
        "last_login": "2026-10-01T11:00:00Z"
      },
      "role": {
        "id": "90ba95ef-206a-464a-b5e0-cb962ba87fe9",
        "name": "Hotel Manager",
        "description": "Full access to rooms and reservations",
        "is_system_role": true,
        "permissions": [
          {
            "code": "rooms.view",
            "name": "View Rooms"
          },
          {
            "code": "rooms.manage",
            "name": "Manage Rooms"
          },
          {
            "code": "reservations.view",
            "name": "View Reservations"
          },
          {
            "code": "reservations.manage",
            "name": "Manage Reservations"
          }
        ],
        "members_count": 1,
        "created_at": "2026-09-28T16:26:00Z"
      },
      "status": "active",
      "joined_at": "2026-09-28T16:26:00Z",
      "permission_codes": [
        "rooms.view",
        "rooms.manage",
        "reservations.view",
        "reservations.manage"
      ]
    }
  ]
}
```

---

## 2. إدارة الفنادق والمستأجرين (`/api/v1/tenants/`)

---

### 2.1 استعراض قائمة الفنادق (List Hotels)
- **URL:** `/api/v1/tenants/hotels/`
- **Method:** `GET`
- **Auth Required:** نعم (Platform Admin Only - `IsPlatformAdmin`)
- **Headers:** `Authorization: Bearer <access_token>`
- **Query Params:**  
  - `page`: رقم الصفحة (افتراضي: `1`)  
  - `page_size`: عدد العناصر (افتراضي: `20`، الحد الأقصى: `100`)

#### Success Response `200 OK`:
```json
{
  "success": true,
  "count": 2,
  "total_pages": 1,
  "current_page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "18c0df1b-31d2-4ef8-a37a-75176b6ef001",
      "name": "Hilton Cairo Heliopolis",
      "slug": "hilton-cairo-heliopolis",
      "subdomain": "hilton-cairo",
      "email": "info@hilton-cairo.com",
      "phone": "+20222677710",
      "address": "El-Orouba, Sheraton Al Matar, El Nozha",
      "city": "Cairo",
      "country": "EG",
      "timezone": "Africa/Cairo",
      "default_currency": "USD",
      "default_language": "en",
      "status": "active",
      "is_active": true,
      "is_operational": true,
      "logo": null,
      "settings": {
        "checkin_time": "14:00:00",
        "checkout_time": "12:00:00",
        "exchange_rate_mode": "manual",
        "allow_overbooking": false,
        "max_advance_booking_days": 365,
        "auto_close_daily": true,
        "invoice_prefix": "INV"
      },
      "created_at": "2026-09-28T16:25:34Z",
      "updated_at": "2026-09-28T16:25:34Z"
    }
  ]
}
```

#### Error Response (مستخدم عادي ليس Platform Admin) `403 Forbidden`:
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Platform admin access required.",
    "details": null,
    "request_id": "4b5dc001-3a0c-4fa7-8bd8-90ab6cd4e201"
  }
}
```

---

### 2.2 إنشاء فندق جديد (Create Hotel)
- **URL:** `/api/v1/tenants/hotels/`
- **Method:** `POST`
- **Auth Required:** نعم (Platform Admin Only)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "name": "Marriott Mena House",
  "slug": "marriott-mena-house",
  "subdomain": "mena-house",
  "email": "info@menahouse.com",
  "phone": "+20233773222",
  "address": "6 Pyramids Road, Giza",
  "city": "Giza",
  "country": "EG",
  "timezone": "Africa/Cairo",
  "default_currency": "EGP",
  "default_language": "ar"
}
```

#### Success Response `201 Created`:
```json
{
  "name": "Marriott Mena House",
  "slug": "marriott-mena-house",
  "subdomain": "mena-house",
  "email": "info@menahouse.com",
  "phone": "+20233773222",
  "address": "6 Pyramids Road, Giza",
  "city": "Giza",
  "country": "EG",
  "timezone": "Africa/Cairo",
  "default_currency": "EGP",
  "default_language": "ar"
}
```
*(ملاحظة: يتم إنشاء كائن `HotelSettings` تلقائياً عبر إشارة Django `post_save` فور إنشاء الفندق).*

#### Error Response (الـ Subdomain مكرر) `400 Bad Request`:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "subdomain: This subdomain is already taken.",
    "details": {
      "subdomain": [
        "This subdomain is already taken."
      ]
    },
    "request_id": "2d9c1234-5678-90ab-cdef-1234567890ab"
  }
}
```

---

### 2.3 جلب تفاصيل فندق محدد (Retrieve Hotel Detail)
- **URL:** `/api/v1/tenants/hotels/{id}/`
- **Method:** `GET`
- **Auth Required:** نعم (Platform Admin Only)
- **Headers:** `Authorization: Bearer <access_token>`

#### Success Response `200 OK`:
```json
{
  "id": "18c0df1b-31d2-4ef8-a37a-75176b6ef001",
  "name": "Hilton Cairo Heliopolis",
  "slug": "hilton-cairo-heliopolis",
  "subdomain": "hilton-cairo",
  "email": "info@hilton-cairo.com",
  "phone": "+20222677710",
  "address": "El-Orouba, Sheraton Al Matar, El Nozha",
  "city": "Cairo",
  "country": "EG",
  "timezone": "Africa/Cairo",
  "default_currency": "USD",
  "default_language": "en",
  "status": "active",
  "is_active": true,
  "is_operational": true,
  "logo": null,
  "settings": {
    "checkin_time": "14:00:00",
    "checkout_time": "12:00:00",
    "exchange_rate_mode": "manual",
    "allow_overbooking": false,
    "max_advance_booking_days": 365,
    "auto_close_daily": true,
    "invoice_prefix": "INV"
  },
  "created_at": "2026-09-28T16:25:34Z",
  "updated_at": "2026-09-28T16:25:34Z"
}
```

#### Error Response (الفندق غير موجود) `404 Not Found`:
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Not found.",
    "details": null,
    "request_id": "3e9b1100-2211-3322-4433-554433221100"
  }
}
```

---

### 2.4 تعديل بيانات فندق بالكامل (Update Hotel - PUT)
- **URL:** `/api/v1/tenants/hotels/{id}/`
- **Method:** `PUT`
- **Auth Required:** نعم (Platform Admin Only)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "name": "Hilton Cairo Luxury Hotel",
  "slug": "hilton-cairo-luxury-hotel",
  "subdomain": "hilton-cairo",
  "email": "gm@hilton-cairo.com",
  "phone": "+20222677710",
  "address": "El-Orouba Road, Heliopolis",
  "city": "Cairo",
  "country": "EG",
  "timezone": "Africa/Cairo",
  "default_currency": "USD",
  "default_language": "en",
  "status": "active",
  "is_active": true
}
```

#### Success Response `200 OK`:
*(يُرجع كائن الفندق المحدث بالكامل مع كائن `settings`).*

---

### 2.5 تعديل جزئي لبيانات فندق (Partial Update Hotel - PATCH)
- **URL:** `/api/v1/tenants/hotels/{id}/`
- **Method:** `PATCH`
- **Auth Required:** نعم (Platform Admin Only)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "phone": "+201099998888",
  "status": "active"
}
```

#### Success Response `200 OK`:
```json
{
  "id": "18c0df1b-31d2-4ef8-a37a-75176b6ef001",
  "name": "Hilton Cairo Luxury Hotel",
  "slug": "hilton-cairo-luxury-hotel",
  "subdomain": "hilton-cairo",
  "email": "gm@hilton-cairo.com",
  "phone": "+201099998888",
  "address": "El-Orouba Road, Heliopolis",
  "city": "Cairo",
  "country": "EG",
  "timezone": "Africa/Cairo",
  "default_currency": "USD",
  "default_language": "en",
  "status": "active",
  "is_active": true,
  "is_operational": true,
  "logo": null,
  "settings": {
    "checkin_time": "14:00:00",
    "checkout_time": "12:00:00",
    "exchange_rate_mode": "manual",
    "allow_overbooking": false,
    "max_advance_booking_days": 365,
    "auto_close_daily": true,
    "invoice_prefix": "INV"
  },
  "created_at": "2026-09-28T16:25:34Z",
  "updated_at": "2026-10-01T11:20:00Z"
}
```

---

### 2.6 حذف فندق (Delete Hotel)
- **URL:** `/api/v1/tenants/hotels/{id}/`
- **Method:** `DELETE`
- **Auth Required:** نعم (Platform Admin Only)
- **Headers:** `Authorization: Bearer <access_token>`

#### Response `204 No Content` *(بدون Body)*

---

## 3. نقاط نهاية النظام والتوثيق والمراقبة (System & Docs)

| المسار (Endpoint) | الميثود | النوع | الوظيفة |
| :--- | :--- | :--- | :--- |
| `/api/schema/` | `GET` | JSON/YAML | ملف مواصفات OpenAPI 3.0 الرسمي لجميع Endpoints المشروع |
| `/api/docs/` | `GET` | HTML / Interactive | واجهة **Swagger UI** التفاعلية لتجربة الـ APIs مباشرة |
| `/api/redoc/` | `GET` | HTML | واجهة **ReDoc** التوثيقية الاحترافية للقراءة والتصدير |
| `/silk/` | `GET` | HTML / Dashboard | واجهة **Django Silk** لفحص استهلاك الذاكرة وزمن كل Request واستعلامات SQL |
| `/__debug__/` | `GET` | Dev Toolbar | شريط فحص Django Debug Toolbar (في وضع DEBUG فقط) |
