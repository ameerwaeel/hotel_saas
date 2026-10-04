# 🌐 دليل جميع الـ Endpoints ونماذج الـ JSON في مشروع HOTEL SaaS

المسار: `docs/endpoints/ALL_ENDPOINTS.md`  
النسخة: `v1.0.0`  
الهدف: توثيق شامل ودقيق لكل نقطة نهاية (API Endpoint) تم بناؤها في المشروع مع شكل الـ JSON الخاص بالطلب (Request) والاستجابة (Response) وحالات الخطأ (Errors).

---

## 📑 فهرس الـ Endpoints

### 1. مصادقة المستخدمين وحسابات الموظفين (`/api/v1/auth/`)
- [1.1 تسجيل مستخدم جديد عادي (Register User)](#11-تسجيل-مستخدم-جديد-عادي-register-user)
- [1.2 تسجيل فندق جديد بالكامل مع المالك (Register Hotel & Owner - Tenant Onboarding)](#12-تسجيل-فندق-جديد-بالكامل-مع-المالك-register-hotel--owner---tenant-onboarding)
- [1.3 استعراض وإضافة موظف للفندق النشط (List & Add/Invite Hotel Member)](#13-استعراض-وإضافة-أعضاء-وموظفي-الفندق-النشط-list--addinvite-hotel-members)
- [1.4 إدارة وإنشاء المستخدمين من قبل مدير المنصة (Platform Admin User Management)](#14-إدارة-وإنشاء-المستخدمين-من-قبل-مدير-المنصة-platform-admin-user-management)
- [1.5 تسجيل الدخول (Login)](#15-تسجيل-الدخول-login)
- [1.6 تسجيل الخروج (Logout)](#16-تسجيل-الخروج-logout)
- [1.7 تجديد Access Token (Token Refresh)](#17-تجديد-access-token-token-refresh)
- [1.8 استرجاع الملف الشخصي الحالي (Get Profile - Me)](#18-استرجاع-الملف-الشخصي-الحالي-get-profile---me)
- [1.9 تعديل الملف الشخصي (Update Profile - Me)](#19-تعديل-الملف-الشخصي-update-profile---me)
- [1.10 تغيير كلمة المرور (Change Password)](#110-تغيير-كلمة-المرور-change-password)
- [1.11 طلب إعادة تعيين كلمة المرور (Password Reset Request)](#111-طلب-إعادة-تعيين-كلمة-المرور-password-reset-request)
- [1.12 تأكيد إعادة تعيين كلمة المرور (Password Reset Confirm)](#112-تأكيد-إعادة-تعيين-كلمة-المرور-password-reset-confirm)
- [1.13 اختيار الفندق النشط (Select Active Hotel)](#113-اختيار-الفندق-النشط-select-active-hotel)
- [1.14 استعراض فنادق وأدوار وصلاحيات المستخدم (My Hotels)](#114-استعراض-فنادق-وأدوار-وصلاحيات-المستخدم-my-hotels)


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

### 1.1 تسجيل مستخدم جديد عادي (Register User)
- **URL:** `/api/v1/auth/register/`
- **Method:** `POST`
- **Auth Required:** لا (Public)
- **Headers:** `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "email": "ameer.waeel99@gmail.com",
  "password": "SecurePassword123!",
  "confirm_password": "SecurePassword123!",
  "first_name": "Ameer",
  "last_name": "Waeel",
  "phone": "+201011223344",
  "preferred_language": "ar"
}
```

#### Success Response `201 Created`:
```json
{
  "success": true,
  "message": "User registered successfully.",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "c4a05c10-ef13-4ab5-b945-166efcc025bf",
      "email": "ameer.waeel99@gmail.com",
      "username": "ameer",
      "first_name": "Ameer",
      "last_name": "Waeel",
      "full_name": "Ameer Waeel",
      "phone": "+201011223344",
      "avatar": null,
      "preferred_language": "ar",
      "is_platform_admin": false,
      "date_joined": "2026-10-01T11:50:00Z",
      "last_login": null
    }
  }
}
```

---

### 1.2 تسجيل فندق جديد بالكامل مع المالك (Register Hotel & Owner - Tenant Onboarding)
- **URL:** `/api/v1/auth/register-hotel/`
- **Method:** `POST`
- **Auth Required:** لا (Public)
- **Headers:** `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "email": "owner@cairopalace.com",
  "password": "StrongPassword123!",
  "first_name": "Karim",
  "last_name": "Hassan",
  "phone": "+201099887766",
  "hotel_name": "Cairo Palace Hotel",
  "subdomain": "cairo-palace",
  "default_currency": "USD",
  "default_language": "en"
}
```

#### Success Response `201 Created`:
```json
{
  "success": true,
  "message": "Hotel and Owner account registered successfully.",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "e4b3c2d1-0000-0000-0000-000000000001",
      "email": "owner@cairopalace.com",
      "username": "owner",
      "first_name": "Karim",
      "last_name": "Hassan",
      "full_name": "Karim Hassan",
      "phone": "+201099887766",
      "avatar": null,
      "preferred_language": "en",
      "is_platform_admin": false,
      "date_joined": "2026-10-01T11:55:00Z",
      "last_login": null
    },
    "hotel": {
      "id": "7fae0176-7bc2-4523-bd0d-13f5635cb049",
      "name": "Cairo Palace Hotel",
      "subdomain": "cairo-palace"
    }
  }
}
```

---

### 1.3 استعراض وإضافة أعضاء وموظفي الفندق النشط (List & Add/Invite Hotel Members)
- **URL:** `/api/v1/auth/members/`
- **Method:** `GET`, `POST`
- **Auth Required:** نعم (عضو فندق نشط `IsHotelMember`)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `X-Hotel-ID: <active_hotel_id>`  
  `Content-Type: application/json`

#### أ) استعراض أعضاء الفندق النشط (GET):
**Request Body:** *فارغ*

**Success Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "hotel_id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
      "hotel_name": "Cairo Palace Hotel",
      "hotel_subdomain": "cairo-palace",
      "user": {
        "id": "f5e4d3c2-b1a0-9876-5432-10fedcba9876",
        "email": "receptionist@cairopalace.com",
        "username": "receptionist",
        "first_name": "Mona",
        "last_name": "Sami",
        "full_name": "Mona Sami",
        "phone": "+201022334455",
        "avatar": null,
        "preferred_language": "en",
        "is_platform_admin": false,
        "date_joined": "2026-10-01T11:58:00Z",
        "last_login": null
      },
      "role": {
        "id": "90ba95ef-206a-464a-b5e0-cb962ba87fe9",
        "name": "Receptionist",
        "description": "Front desk and checkin operations",
        "is_system_role": false,
        "permissions": [
          {
            "code": "rooms.view",
            "name": "View Rooms"
          }
        ],
        "members_count": 1,
        "created_at": "2026-10-01T11:00:00Z"
      },
      "status": "active",
      "joined_at": "2026-10-01T11:58:00Z",
      "permission_codes": [
        "rooms.view"
      ]
    }
  ]
}
```

#### ب) إضافة/دعوة عضو جديد للفندق (POST):
**Request Body (JSON):**
```json
{
  "email": "receptionist@cairopalace.com",
  "role_id": "90ba95ef-206a-464a-b5e0-cb962ba87fe9",
  "first_name": "Mona",
  "last_name": "Sami",
  "phone": "+201022334455",
  "password": "TempPassword123!"
}
```

**Success Response `201 Created`:**
```json
{
  "success": true,
  "message": "Member added to hotel successfully.",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "hotel_id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
    "hotel_name": "Cairo Palace Hotel",
    "hotel_subdomain": "cairo-palace",
    "user": {
      "id": "f5e4d3c2-b1a0-9876-5432-10fedcba9876",
      "email": "receptionist@cairopalace.com",
      "username": "receptionist",
      "first_name": "Mona",
      "last_name": "Sami",
      "full_name": "Mona Sami",
      "phone": "+201022334455",
      "avatar": null,
      "preferred_language": "en",
      "is_platform_admin": false,
      "date_joined": "2026-10-01T11:58:00Z",
      "last_login": null
    },
    "role": {
      "id": "90ba95ef-206a-464a-b5e0-cb962ba87fe9",
      "name": "Receptionist",
      "description": "Front desk and checkin operations",
      "is_system_role": false,
      "permissions": [
        {
          "code": "rooms.view",
          "name": "View Rooms"
        }
      ],
      "members_count": 1,
      "created_at": "2026-10-01T11:00:00Z"
    },
    "status": "active",
    "joined_at": "2026-10-01T11:58:00Z",
    "permission_codes": [
      "rooms.view"
    ]
  }
}
```


---

### 1.4 إدارة وإنشاء المستخدمين من قبل مدير المنصة (Platform Admin User Management)
- **URL:**  
  - `GET /api/v1/auth/users/` (قائمة المستخدمين في المنصة)  
  - `POST /api/v1/auth/users/` (إنشاء مستخدم أو مدير منصة جديد)  
  - `GET /api/v1/auth/users/{id}/` (تفاصيل مستخدم)  
  - `PATCH /api/v1/auth/users/{id}/` (تعديل مستخدم)  
  - `DELETE /api/v1/auth/users/{id}/` (حذف مستخدم)
- **Method:** `GET`, `POST`, `PATCH`, `DELETE`
- **Auth Required:** نعم (`IsPlatformAdmin`)
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `Content-Type: application/json`

#### Request Body لإنشاء مستخدم (POST):
```json
{
  "email": "newadmin@saas.com",
  "password": "AdminPassword123!",
  "first_name": "System",
  "last_name": "Administrator",
  "phone": "+201011112222",
  "is_platform_admin": true,
  "is_staff": true,
  "is_active": true,
  "preferred_language": "en"
}
```

#### Success Response `201 Created`:
```json
{
  "id": "d4e5f6a7-b8c9-0123-4567-89abcdef0123",
  "email": "newadmin@saas.com",
  "username": "newadmin",
  "first_name": "System",
  "last_name": "Administrator",
  "full_name": "System Administrator",
  "phone": "+201011112222",
  "avatar": null,
  "preferred_language": "en",
  "is_platform_admin": true,
  "date_joined": "2026-10-01T12:00:00Z",
  "last_login": null
}
```

---

### 1.5 تسجيل الدخول (Login)
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
- **Headers:**  
  `Authorization: Bearer <access_token>`  
  `X-Hotel-ID: <active_hotel_id>` (اختياري، لجلب دور وصلاحيات الفندق)

#### Request Body: *فارغ*

#### Success Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "id": "5e3dd943-5a1b-49f4-ab7b-ab76df21216b",
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
  "message": "If this email exists in our system, a password reset email has been sent."
}
```

---

### 1.8 تأكيد إعادة تعيين كلمة المرور (Password Reset Confirm)
- **URL:** `/api/v1/auth/reset-password-confirm/`
- **Method:** `POST`
- **Auth Required:** لا (Public)
- **Headers:** `Content-Type: application/json`

#### Request Body (JSON):
```json
{
  "uid": "NQ",
  "token": "d7s1z2-3844d1f2e82abcb471ad98bc203498f2",
  "new_password": "NewStrongPassword456!",
  "confirm_password": "NewStrongPassword456!"
}
```

#### Success Response `200 OK`:
```json
{
  "success": true,
  "message": "Password has been reset successfully. You can now log in with your new password."
}
```

#### Error Response (رمز غير صالح أو منتهي) `400 Bad Request`:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Token is invalid or expired."
  }
}
```

---

### 1.9 اختيار الفندق النشط (Select Active Hotel)

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

### 1.10 استعراض فنادق وأدوار وصلاحيات المستخدم (My Hotels)
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
      "hotel_id": "18c0df1b-31d2-4ef8-a37a-75176b6ef001",
      "hotel_name": "Hilton Cairo Heliopolis",
      "hotel_subdomain": "hilton-cairo",
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

---

## 4. Phase 4 — Master Data: Rooms, Customers, Employees

### 4.1 Languages & Hotel Languages (`/api/v1/rooms/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/rooms/languages/` | List all active global languages | JWT |
| `GET` | `/api/v1/rooms/hotel-languages/` | List languages configured for the active hotel | JWT |
| `POST` | `/api/v1/rooms/hotel-languages/` | Add a language to the active hotel | JWT + `rooms.manage` |
| `DELETE` | `/api/v1/rooms/hotel-languages/{id}/` | Remove a language from the hotel | JWT + `rooms.manage` |
| `PATCH` | `/api/v1/rooms/hotel-languages/{id}/set-default/` | Set a language as the hotel's default | JWT + `rooms.manage` |

### 4.2 Booking Sources (`/api/v1/rooms/booking-sources/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/rooms/booking-sources/` | List all active booking sources for the hotel | JWT + `rooms.view` |
| `POST` | `/api/v1/rooms/booking-sources/` | Create a new booking source | JWT + `rooms.manage` |
| `GET` | `/api/v1/rooms/booking-sources/{id}/` | Retrieve a specific booking source | JWT + `rooms.view` |
| `PUT` | `/api/v1/rooms/booking-sources/{id}/` | Full update of a booking source | JWT + `rooms.manage` |
| `PATCH` | `/api/v1/rooms/booking-sources/{id}/` | Partial update of a booking source | JWT + `rooms.manage` |
| `DELETE` | `/api/v1/rooms/booking-sources/{id}/` | Deactivate (soft-delete) booking source | JWT + `rooms.manage` |

### 4.3 Room Types & Translations (`/api/v1/rooms/room-types/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/rooms/room-types/` | List room types with translations for the hotel | JWT + `rooms.view` |
| `POST` | `/api/v1/rooms/room-types/` | Create a new room type with translations | JWT + `rooms.manage` |
| `GET` | `/api/v1/rooms/room-types/{id}/` | Retrieve a room type with all translations | JWT + `rooms.view` |
| `PUT` | `/api/v1/rooms/room-types/{id}/` | Full update of a room type | JWT + `rooms.manage` |
| `PATCH` | `/api/v1/rooms/room-types/{id}/` | Partial update of a room type | JWT + `rooms.manage` |
| `DELETE` | `/api/v1/rooms/room-types/{id}/` | Delete a room type (if no active rooms) | JWT + `rooms.manage` |

### 4.4 Rooms (`/api/v1/rooms/rooms/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/rooms/rooms/` | List all rooms with current status | JWT + `rooms.view` |
| `POST` | `/api/v1/rooms/rooms/` | Create a new room | JWT + `rooms.manage` |
| `GET` | `/api/v1/rooms/rooms/{id}/` | Retrieve room detail | JWT + `rooms.view` |
| `PUT` | `/api/v1/rooms/rooms/{id}/` | Full update of a room | JWT + `rooms.manage` |
| `PATCH` | `/api/v1/rooms/rooms/{id}/` | Partial update of a room | JWT + `rooms.manage` |

### 4.5 Customers (`/api/v1/customers/customers/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/customers/customers/` | List customers for the hotel (with search) | JWT + `customers.view` |
| `POST` | `/api/v1/customers/customers/` | Create a new customer | JWT + `customers.manage` |
| `GET` | `/api/v1/customers/customers/{id}/` | Retrieve customer detail with stay history | JWT + `customers.view` |
| `PUT` | `/api/v1/customers/customers/{id}/` | Full update of customer record | JWT + `customers.manage` |
| `PATCH` | `/api/v1/customers/customers/{id}/` | Partial update of customer record | JWT + `customers.manage` |

### 4.6 Employees (`/api/v1/customers/employees/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/customers/employees/` | List employees for the hotel | JWT + `customers.view` |
| `POST` | `/api/v1/customers/employees/` | Create a new employee record | JWT + `customers.manage` |
| `GET` | `/api/v1/customers/employees/{id}/` | Retrieve employee detail | JWT + `customers.view` |
| `PUT` | `/api/v1/customers/employees/{id}/` | Full update of employee record | JWT + `customers.manage` |
| `PATCH` | `/api/v1/customers/employees/{id}/` | Partial update of employee record | JWT + `customers.manage` |

---

## 5. Phase 5 — Reservations + Availability Engine

### 5.1 Reservations (`/api/v1/reservations/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reservations/` | List all reservations for the hotel (filterable by status/date) | JWT + `reservations.view` |
| `POST` | `/api/v1/reservations/` | Create a new reservation (with room assignment) | JWT + `reservations.manage` |
| `GET` | `/api/v1/reservations/{id}/` | Retrieve reservation detail with all rooms | JWT + `reservations.view` |
| `PATCH` | `/api/v1/reservations/{id}/` | Update reservation details (special requests, etc.) | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/confirm/` | Transition reservation: PENDING → CONFIRMED | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/cancel/` | Transition reservation: PENDING/CONFIRMED → CANCELLED | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/check-in/` | Transition reservation: CONFIRMED → CHECKED_IN; sets rooms OCCUPIED | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/check-out/` | Transition: CHECKED_IN → CHECKED_OUT; creates cleaning tasks | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/no-show/` | Transition reservation: CONFIRMED → NO_SHOW | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/upgrade-room/` | Upgrade a room within the reservation; creates change record | JWT + `reservations.manage` |

### 5.2 Availability Engine (`/api/v1/reservations/availability/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reservations/availability/` | Query available rooms for given check_in & check_out dates | JWT + `reservations.view` |

---

## 6. Phase 6 — Payments + Finance + Closings

### 6.1 Payment Methods (`/api/v1/payments/methods/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/payments/methods/` | List all active payment methods for the hotel | JWT + `payments.view` |
| `POST` | `/api/v1/payments/methods/` | Create a new payment method | JWT + `payments.manage` |
| `PATCH` | `/api/v1/payments/methods/{id}/` | Update a payment method | JWT + `payments.manage` |

### 6.2 Payments (`/api/v1/payments/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/payments/` | List payments with filters (date, reservation, currency) | JWT + `payments.view` |
| `POST` | `/api/v1/payments/` | Record a new payment (auto-creates FinancialTransaction) | JWT + `payments.manage` |
| `GET` | `/api/v1/payments/{id}/` | Retrieve payment detail | JWT + `payments.view` |
| `DELETE` | `/api/v1/payments/{id}/` | Soft-delete a payment (preserves audit trail) | JWT + `payments.manage` |

### 6.3 Finance Categories (`/api/v1/finance/categories/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/finance/categories/` | List finance categories (INCOME/EXPENSE) | JWT + `finance.view` |
| `POST` | `/api/v1/finance/categories/` | Create a new finance category | JWT + `finance.manage` |
| `PATCH` | `/api/v1/finance/categories/{id}/` | Update a finance category | JWT + `finance.manage` |

### 6.4 Financial Transactions (`/api/v1/finance/transactions/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/finance/transactions/` | List financial transactions with filters | JWT + `finance.view` |
| `POST` | `/api/v1/finance/transactions/` | Create a manual financial transaction | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/transactions/{id}/` | Retrieve transaction detail | JWT + `finance.view` |
| `DELETE` | `/api/v1/finance/transactions/{id}/` | Soft-delete transaction (audit trail preserved) | JWT + `finance.manage` |

### 6.5 Financial Summary (`/api/v1/finance/summary/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/finance/summary/daily/` | Daily income/expense summary grouped by currency | JWT + `finance.view` |

### 6.6 Daily & Monthly Closings (`/api/v1/finance/closings/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/finance/closings/daily/` | List all daily closings for the hotel | JWT + `finance.view` |
| `POST` | `/api/v1/finance/closings/daily/` | Close a specific day (idempotent, select_for_update) | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/closings/monthly/` | List all monthly closings | JWT + `finance.view` |
| `POST` | `/api/v1/finance/closings/monthly/` | Close a month (requires all daily closings to be CLOSED) | JWT + `finance.manage` |

### 6.7 Exchange Rates (`/api/v1/finance/exchange-rates/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/finance/exchange-rates/` | List stored exchange rates (display only) | JWT + `finance.view` |
| `POST` | `/api/v1/finance/exchange-rates/` | Add an exchange rate entry | JWT + `finance.manage` |

### 6.8 Async Financial Export (`/api/v1/finance/export/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/finance/export/` | Trigger async report export; returns `task_id` immediately | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/export/{task_id}/status/` | Poll Celery task status; returns download URL on completion | JWT + `finance.view` |

---

## 7. Phase 7 — Housekeeping + Maintenance + Complaints

### 7.1 Housekeeping / Cleaning Tasks (`/api/v1/housekeeping/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/housekeeping/cleanings/` | List all cleaning tasks (filterable by status/date/room) | JWT + `housekeeping.view` |
| `POST` | `/api/v1/housekeeping/cleanings/` | Manually create a cleaning task | JWT + `housekeeping.manage` |
| `GET` | `/api/v1/housekeeping/cleanings/{id}/` | Retrieve cleaning task detail | JWT + `housekeeping.view` |
| `PATCH` | `/api/v1/housekeeping/cleanings/{id}/` | Update cleaning task notes/schedule | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/assign/` | Assign a housekeeper to the cleaning task | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/start/` | Transition: PENDING → IN_PROGRESS | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/complete/` | Transition: IN_PROGRESS → COMPLETED | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/inspect/` | Transition: COMPLETED → INSPECTED; triggers mark_available() | JWT + `housekeeping.manage` |

### 7.2 Maintenance Issues (`/api/v1/maintenance/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/maintenance/issues/` | List all maintenance issues (filterable by priority/status/room) | JWT + `maintenance.view` |
| `POST` | `/api/v1/maintenance/issues/` | Report a new maintenance issue | JWT + `maintenance.manage` |
| `GET` | `/api/v1/maintenance/issues/{id}/` | Retrieve maintenance issue detail | JWT + `maintenance.view` |
| `PATCH` | `/api/v1/maintenance/issues/{id}/` | Update issue details (assign, priority, blocking flag) | JWT + `maintenance.manage` |
| `POST` | `/api/v1/maintenance/issues/{id}/resolve/` | Transition: IN_PROGRESS → RESOLVED with resolution notes | JWT + `maintenance.manage` |

### 7.3 Customer Complaints (`/api/v1/complaints/`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/complaints/` | List all complaints (filterable by status/priority) | JWT + `complaints.view` |
| `POST` | `/api/v1/complaints/` | Create a new customer complaint | JWT + `complaints.manage` |
| `GET` | `/api/v1/complaints/{id}/` | Retrieve complaint detail | JWT + `complaints.view` |
| `PATCH` | `/api/v1/complaints/{id}/` | Update complaint details | JWT + `complaints.manage` |
| `POST` | `/api/v1/complaints/{id}/assign/` | Assign complaint to a staff member | JWT + `complaints.manage` |
| `POST` | `/api/v1/complaints/{id}/resolve/` | Resolve complaint with resolution notes | JWT + `complaints.manage` |

