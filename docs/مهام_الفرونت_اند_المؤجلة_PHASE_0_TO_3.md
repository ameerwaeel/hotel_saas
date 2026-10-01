# 🎨 دليل مهام الواجهة الأمامية المؤجلة (Frontend Roadmap: Phase 0 - Phase 3)
## Master Deferred Tasks for React / Vite Frontend (Authentication, Multi-Tenancy & Core Shell)

**المسار:** `docs/مهام_الفرونت_اند_المؤجلة_PHASE_0_TO_3.md`  
*(النسخة الإنجليزية الموازية: [`docs/FRONTEND_DEFERRED_TASKS_PHASE_0_TO_3.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/FRONTEND_DEFERRED_TASKS_PHASE_0_TO_3.md))*  
**المشروع:** HOTEL SaaS Platform  
**الحالة:** تجميع شامل لكافة متطلبات وتاسكات الفرونت إند المؤجلة من المرحلة 0 وحتى المرحلة 3، متضمنة معمارية الكود، الـ State Management، الشاشات، والـ Hooks الجاهزة للتنفيذ.

---

## 📑 فهرس محتويات الدليل

1. [نظرة عامة والقرار المعماري](#1-نظرة-عامة-والقرار-المعماري)
2. [تاسكات المرحلة 0 — تهيئة مشروع React Vite والبنية الأساسية](#2-تاسكات-المرحلة-0--تهيئة-مشروع-react-vite-والبنية-الأساسية)
3. [تاسكات المرحلة 1 — عميل الـ API، معالجة الأخطاء، والتخطيط العام (Shell Layout)](#3-تاسكات-المرحلة-1--عميل-الـ-api-معالجة-الأخطاء-والتخطيط-العام-shell-layout)
4. [تاسكات المرحلة 2 — سياق الفندق النشط والتبديل بين الفنادق (Multi-Tenancy UI)](#4-تاسكات-المرحلة-2--سياق-الفندق-النشط-والتبديل-بين-الفنادق-multi-tenancy-ui)
5. [تاسكات المرحلة 3 — شاشات المصادقة، الأدوار، والصلاحيات (Auth & RBAC UI)](#5-تاسكات-المرحلة-3--شاشات-المصادقة-الأدوار-والصلاحيات-auth--rbac-ui)
6. [قائمة الشاشات والمكونات التفصيلية (Screen-by-Screen Breakdown)](#6-قائمة-الشاشات-والمكونات-التفصيلية-screen-by-screen-breakdown)
7. [الـ Hooks والمكونات الحارسة الجاهزة للتنفيذ (Guards & Custom Hooks)](#7-الـ-hooks-والمكونات-الحارسة-الجاهزة-للتنفيذ-guards--custom-hooks)
8. [جدول ربط نقاط النهاية (API Endpoints Integration Matrix)](#8-جدول-ربط-نقاط-النهاية-api-endpoints-integration-matrix)

---

## 1. نظرة عامة والقرار المعماري

بناءً على التوجيه المعماري:
> **"تم التركيز أولاً على بناء واختبار كافة الـ Backend APIs ونظام عزل البيانات وقواعد البيانات والصلاحيات، وتأجيل الواجهات الأمامية (Frontend) مع توثيق كافة تفاصيلها لنعود إليها ككتلة واحدة متكاملة ومستقرة."**

هذا المستند هو المرجع التنفيذي الدقيق لفريق الواجهة الأمامية، بحيث عند البدء بالفرونت إند لا نحتاج للتفكير في الـ Contracts أو تخمين شكل البيانات، فكل شيء محدد ومربوط بالـ Endpoints الجاهزة في الباك إند بنسبة 100%.

---

## 2. تاسكات المرحلة 0 — تهيئة مشروع React Vite والبنية الأساسية

### 🛠️ المهام التقنية المطلوبة (Tasks Checklist):
- [ ] **إنشاء مشروع React حديث باستخدام Vite:**
  ```bash
  npm create vite@latest frontend -- --template react-ts
  cd frontend
  npm install
  ```
- [ ] **تثبيت المكتبات المعتمدة في الخطة:**
  ```bash
  npm install react-router-dom axios lucide-react clsx tailwind-merge
  npm install react-i18next i18next i18next-browser-languagedetector
  npm install react-hook-form @hookform/resolvers zod
  npm install @tanstack/react-query
  npm install -D tailwindcss postcss autoprefixer
  ```
- [ ] **إعداد هيكلية المجلدات القياسية للمشروع:**
  ```
  frontend/src/
  ├── app/                  # المزودات العامة (Providers, Router Setup)
  │   ├── App.tsx
  │   ├── router.tsx
  │   └── providers.tsx
  ├── core/                 # الوحدات المركزية المشتركة
  │   ├── api/              # Axios Client, Interceptors, Token Management
  │   ├── auth/             # AuthContext, AuthProvider, useAuth
  │   ├── tenant/           # HotelContext, HotelProvider, useHotel
  │   ├── permissions/      # useHasPermission, PermissionGuard, ProtectedRoute
  │   ├── i18n/             # إعدادات اللغات (ar/en) ودعم الـ RTL/LTR
  │   └── layouts/          # DashboardLayout, AuthLayout, PublicLayout
  ├── modules/              # شاشات الموديولات الوظيفية
  │   ├── auth/             # Login, Register, RegisterHotel, ResetPassword
  │   ├── profile/          # ProfilePage, ChangePasswordModal
  │   ├── members/          # HotelMembersList, InviteMemberModal
  │   └── admin/            # PlatformUsersManagement
  └── shared/               # مكونات UI قابلة لإعادة الاستخدام
      ├── components/       # Button, Input, Modal, Badge, Dropdown, Table
      ├── feedback/         # LoadingState, ErrorState, EmptyState, Toast
      └── utils/            # formatters, helpers
  ```
- [ ] **ضبط الـ Proxy في `vite.config.ts` لربط طلبات الباك إند بسلاسة:**
  ```typescript
  export default defineConfig({
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  });
  ```
- [ ] **تهيئة دعم العربية والإنجليزية والـ RTL/LTR (`core/i18n`):**
  - ربط ملفات الترجمة `ar.json` و `en.json`.
  - تبديل اتجاه المستند `document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr'`.

---

## 3. تاسكات المرحلة 1 — عميل الـ API، معالجة الأخطاء، والتخطيط العام (Shell Layout)

### 🛠️ المهام التقنية المطلوبة (Tasks Checklist):
- [ ] **بناء العميل البرمجي المركزي `core/api/client.ts`:**
  - إعداد مثيل Axios مع Base URL مضبوط على `/api/v1/`.
  - ترويسات افتراضية `Content-Type: application/json` و `Accept: application/json`.
- [ ] **كتابة الـ Axios Interceptors للتعامل التلقائي مع الأخطاء والتوكنات:**
  1. **Request Interceptor:**
     - حقن الـ `Authorization: Bearer <accessToken>` في الترويسة إذا كان المستخدم مسجلاً.
     - حقن ترويسة الفندق النشط `X-Hotel-ID: <activeHotelId>` في كل طلب تلقائياً.
  2. **Response Interceptor:**
     - اعتراض أخطاء `401 Unauthorized`: استدعاء آلية Silent Token Refresh (تجديد التوكن التلقائي).
     - اعتراض أخطاء `403 Forbidden`: عرض تنبيه بعدم امتلاك الصلاحية اللازمة.
     - استخراج رسالة الخطأ الموحدة من رد الباك إند:
       `response.data.error.message` وعرضها للمستخدم.
- [ ] **بناء مكونات التغذية الراجعة المشتركة (Shared Feedback Components):**
  - `LoadingState`: مؤشر تحميل أنيق (Spinner أو Skeleton Loader).
  - `ErrorState`: كارت عرض الخطأ مع زر لإعادة المحاولة (Retry).
  - `EmptyState`: كارت لطيف يظهر عند عدم وجود بيانات مع أيقونة وزر إجراء (Action).
- [ ] **بناء التخطيط العام للوحة التحكم (Dashboard Shell Layout):**
  - `Sidebar`: قائمة التنقل الجانبية مع إخفاء الموديولات التي لا يملك الموظف صلاحية عليها.
  - `Topbar`: شريط علوي يحتوي على:
    - محول الفنادق النشطة (Hotel Switcher Dropdown).
    - محول اللغة (AR / EN).
    - زر الوضع الليلي/النهاري.
    - قائمة الملف الشخصي وزر تسجيل الخروج.

---

## 4. تاسكات المرحلة 2 — سياق الفندق النشط والتبديل بين الفنادق (Multi-Tenancy UI)

### 🛠️ المهام التقنية المطلوبة (Tasks Checklist):
- [ ] **بناء سياق الفندق `core/tenant/HotelContext.tsx`:**
  - حفظ حالة الفندق النشط:
    ```typescript
    interface ActiveHotel {
      id: string;
      name: string;
      subdomain: string;
      currency?: string;
      timezone?: string;
    }
    ```
  - مزامنة الفندق النشط مع `localStorage` لضمان بقائه عند تحديث الصفحة (Refresh).
  - دالة `switchHotel(hotelId: string)`:
    - ترسل طلب `POST /api/v1/auth/select-hotel/`.
    - تحدث الترويسة `X-Hotel-ID`.
    - تعيد تحميل بيانات الشاشة والـ Cache لتصفية البيانات تبعاً للفندق الجديد.
- [ ] **بناء مكون التبديل بين الفنادق (Hotel Switcher Component):**
  - استدعاء `GET /api/v1/auth/my-hotels/` لعرض قائمة الفنادق التي ينتمي إليها الموظف مع دوره في كل فندق.
  - تمييز الفندق المحدد حالياً برمز صح (Checkmark).
  - في حال كان المستخدم `Platform Admin`، إتاحة إمكانية اختيار أي فندق في المنصة لإدارته.

---

## 5. تاسكات المرحلة 3 — شاشات المصادقة، الأدوار، والصلاحيات (Auth & RBAC UI)

### 🛠️ المهام التقنية المطلوبة (Tasks Checklist):
- [ ] **بناء سياق المصادقة المركزي `core/auth/AuthContext.tsx`:**
  - تخزين بيانات المستخدم المسجل، وحالة الدخول `isAuthenticated`.
  - إدارة وحفظ الـ Access Token و Refresh Token.
  - دالة `login(email, password)`: ترسل لـ `/api/v1/auth/login/`، وتخزن التوكنات، ثم تستدعي جلب الفنادق النشطة.
  - دالة `logout()`: ترسل `POST /api/v1/auth/logout/` مع الـ `refresh` token لإضافته للقائمة السوداء، ثم تمسح البيانات من المتصفح وتوجه إلى `/login`.
- [ ] **دورة التجديد الصامت للتوكن (Silent Token Refresh Flow):**
  - عند استلام كود 401، يقوم الـ Interceptor بتعليق الطلبات الواردة (Request Queue)، وإرسال طلب `POST /api/v1/auth/token/refresh/` بـ Refresh Token الحالي.
  - عند النجاح: تحديث الـ Access Token وإعادة تنفيذ كافة الطلبات المعلقة دون أن يشعر المستخدم بأي تقطع.
  - عند الفشل: إتمام تسجيل الخروج وإعادة التوجيه لصفحة تسجيل الدخول.
- [ ] **نظام حماية الواجهة بالصلاحيات (Frontend RBAC Engine):**
  - بناء Hook مخصص `useHasPermission(code: string): boolean`.
  - بناء مكون `<PermissionGuard permission="rooms.view">` لإخفاء أو تعطيل الأزرار والشاشات.
  - بناء مكون `<ProtectedRoute>` لمنع المستخدم من كتابة رابط شاشة في المتصفح والدخول إليها إذا لم يكن مصرحاً له.

---

## 6. قائمة الشاشات والمكونات التفصيلية (Screen-by-Screen Breakdown)

### 1. شاشة تسجيل الدخول (`/login`)
- **المدخلات:** البريد الإلكتروني، كلمة المرور، خيار "تذكرني".
- **التحقق (Validation):** بريد صالح، كلمة مرور مطلوبة.
- **الإجراء:** إرسال `POST /api/v1/auth/login/`.
- **التوجيه:** التوجيه إلى `/dashboard` بعد النجاح واختيار الفندق الأول افتراضياً.
- **روابط إضافية:** "نسيت كلمة المرور؟"، "تسجيل فندق جديد".

### 2. شاشة تسجيل مستخدم جديد عادي (`/register`)
- **المدخلات:** الاسم الأول، الاسم الأخير، البريد الإلكتروني، كلمة المرور، تأكيد كلمة المرور، رقم الهاتف، اللغة المفضلة.
- **الإجراء:** إرسال `POST /api/v1/auth/register/`.
- **الاستجابة:** استلام التوكنات وحفظ الجلسة والدخول للمنصة.

### 3. شاشة تسجيل فندق جديد بالكامل مع المالك Onboarding (`/register-hotel`)
- **معالج الخطوات (Step Wizard):**
  - الخطوة 1 (بيانات المالك): الاسم، البريد الإلكتروني، كلمة المرور، الهاتف.
  - الخطوة 2 (بيانات الفندق): اسم الفندق، النطاق الفرعي المطلوب (`subdomain`)، العملة الافتراضية، اللغة الافتراضية.
- **الإجراء:** إرسال `POST /api/v1/auth/register-hotel/`.
- **النتيجة:** إنشاء الفندق والمالك وتفعيل دور `Owner` تلقائياً، وتوجيه المالك إلى لوحة تحكم فندقه الجديد مباشرة.

### 4. شاشة طلب استعادة كلمة المرور (`/reset-password`)
- **المدخلات:** البريد الإلكتروني.
- **الإجراء:** إرسال `POST /api/v1/auth/reset-password/`.
- **الاستجابة:** رسالة نجاح واضحة: *"إذا كان هذا البريد مسجلاً لدينا، فقد تم إرسال رابط ورمز الاستعادة إلى بريدك الإلكتروني"*.

### 5. شاشة تأكيد كلمة المرور الجديدة (`/reset-password-confirm`)
- **المدخلات:** الـ `uid` والـ `token` (يتم استخراجهما تلقائياً من رابط البريد أو إدخالهما يدوياً)، كلمة المرور الجديدة، تأكيد كلمة المرور.
- **الإجراء:** إرسال `POST /api/v1/auth/reset-password-confirm/`.
- **النتيجة:** تأكيد التغيير والتحويل لصفحة تسجيل الدخول.

### 6. شاشة الملف الشخصي الحالية (`/profile` أو `/me`)
- **البيانات المعروضة:**
  - الاسم الكامل، البريد، الهاتف، تاريخ الانضمام.
  - كارت الفندق النشط حالياً (`active_hotel`): اسمه ونطاقه وعملته.
  - الدور الحالي للموظف في هذا الفندق (`current_role`).
  - قائمة الصلاحيات المفعلة له (`permissions` badges).
- **الإجراءات المتاحة:**
  - تعديل البيانات الشخصية (`PATCH /api/v1/auth/me/`).
  - فتح نافذة منبثقة (Modal) لتغيير كلمة المرور (`POST /api/v1/auth/change-password/`).

### 7. شاشة موظفي وأعضاء الفندق النشط (`/members`)
- **صلاحية الدخول:** تتطلب دور مدير فندق أو مالك (`IsHotelMember`).
- **المحتوى:**
  - جدول يعرض موظفي الفندق الحالي مسترجعاً من `GET /api/v1/auth/members/`.
  - أعمدة الجدول: الاسم، البريد، الهاتف، الدور الحالي، تاريخ الانضمام، وحالة العضوية (نشط/معطل).
- **نافذة إضافة أو دعوة موظف جديد (Modal):**
  - حقول: البريد الإلكتروني، الاسم، الهاتف، اختيار الدور من القائمة (`role_id`)، وكلمة مرور مؤقتة (اختيارية).
  - عند الحفظ: إرسال `POST /api/v1/auth/members/` وإظهار تنبيه بإرسال بريد ترحيبي للموظف.

### 8. شاشة إدارة مستخدمي المنصة (Platform Admin Users: `/admin/users`)
- **صلاحية الدخول:** محصورة بمدراء المنصة (`is_platform_admin = true`).
- **المحتوى:** جدول كامل بكافة مستخدمي المنصة (`GET /api/v1/auth/users/`) مع إمكانية إضافة مستخدم أو مدير منصة جديد، وتعديل الصلاحيات أو الحظر.

---

## 7. الـ Hooks والمكونات الحارسة الجاهزة للتنفيذ (Guards & Custom Hooks)

لتسريع عمل فريق الفرونت إند لاحقاً، تم تصميم الهيكل البرمجي الجاهز لهذه المكونات:

### 1. الـ Hook الخاص بالصلاحيات `useHasPermission`:
```typescript
// core/permissions/useHasPermission.ts
import { useAuth } from '../auth/AuthContext';

export const useHasPermission = (permissionCode: string): boolean => {
  const { user } = useAuth();
  
  if (!user) return false;
  // مدراء المنصة يملكون كامل الصلاحيات
  if (user.is_platform_admin || user.permissions?.includes('*')) return true;
  
  return user.permissions?.includes(permissionCode) ?? false;
};
```

### 2. المكون الحارس `PermissionGuard`:
```tsx
// core/permissions/PermissionGuard.tsx
import React from 'react';
import { useHasPermission } from './useHasPermission';

interface Props {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const PermissionGuard: React.FC<Props> = ({ permission, children, fallback = null }) => {
  const hasAccess = useHasPermission(permission);
  if (!hasAccess) return <>{fallback}</>;
  return <>{children}</>;
};
```

### 3. مكون حماية المسارات `ProtectedRoute`:
```tsx
// core/permissions/ProtectedRoute.tsx
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { LoadingState } from '../../shared/feedback/LoadingState';

interface Props {
  requiredPermission?: string;
}

export const ProtectedRoute: React.FC<Props> = ({ requiredPermission }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) return <LoadingState />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  if (requiredPermission) {
    const hasPerm = user?.is_platform_admin || user?.permissions?.includes(requiredPermission);
    if (!hasPerm) return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
};
```

---

## 8. جدول ربط نقاط النهاية (API Endpoints Integration Matrix)

هذا الجدول يوضح الشاشة في الواجهة الأمامية ونقطة النهاية المقابلة لها في الباك إند:

| الشاشة في الـ Frontend | Endpoint الباك إند | نوع الطلب HTTP | الحقول المطلوبة في الطلب (Body) | الملاحظات |
| :--- | :--- | :--- | :--- | :--- |
| **تسجيل الدخول** | `/api/v1/auth/login/` | `POST` | `email`, `password` | يعيد `access`, `refresh`, وبيانات `user`. |
| **تسجيل مستخدم** | `/api/v1/auth/register/` | `POST` | `email`, `password`, `confirm_password`, `first_name`, `last_name`, `phone` | تسجيل فوري وإرجاع التوكنات. |
| **تسجيل فندق ومالك** | `/api/v1/auth/register-hotel/` | `POST` | بيانات المالك + `hotel_name`, `subdomain`, `default_currency` | عملية ذرية واحدة (Tenant Onboarding). |
| **تجديد التوكن** | `/api/v1/auth/token/refresh/` | `POST` | `refresh` | يستدعى تلقائياً عبر الـ Interceptor عند كود 401. |
| **تسجيل الخروج** | `/api/v1/auth/logout/` | `POST` | `refresh` | إلغاء الجلسة وإضافة التوكن للـ Blacklist. |
| **قراءة الملف الشخصي** | `/api/v1/auth/me/` | `GET` | *فارغ* (مع ترويسة `X-Hotel-ID`) | يعيد المستخدم، الفندق النشط، دوره، وصلاحياته. |
| **تعديل الملف الشخصي** | `/api/v1/auth/me/` | `PATCH` | `first_name`, `last_name`, `phone`, `preferred_language` | تعديل جزئي للبيانات الشخصية. |
| **تغيير كلمة المرور** | `/api/v1/auth/change-password/` | `POST` | `old_password`, `new_password`, `confirm_password` | للمستخدم المسجل الحالي. |
| **طلب استعادة المرور** | `/api/v1/auth/reset-password/` | `POST` | `email` | يرسل البريد الحقيقي مع الـ token و uid. |
| **تأكيد استعادة المرور**| `/api/v1/auth/reset-password-confirm/`| `POST` | `uid`, `token`, `new_password`, `confirm_password` | تحديث كلمة المرور للجديدة. |
| **قائمة فنادق المستخدم**| `/api/v1/auth/my-hotels/` | `GET` | *فارغ* | تغذية قائمة اختيار الفنادق (Switcher). |
| **اختيار الفندق النشط**| `/api/v1/auth/select-hotel/` | `POST` | `hotel_id` | تثبيت الفندق النشط في الجلسة. |
| **قائمة موظفي الفندق** | `/api/v1/auth/members/` | `GET` | *فارغ* (مع ترويسة `X-Hotel-ID`) | استعراض موظفي وأدوار الفندق النشط. |
| **إضافة موظف للفندق** | `/api/v1/auth/members/` | `POST` | `email`, `role_id`, `first_name`, `last_name`, `password` | إضافة عضو وإرسال بريد دعوة ترحيبي. |
| **إدارة مستخدمي المنصة**| `/api/v1/auth/users/` | `GET`, `POST`, `PATCH`, `DELETE` | بيانات المستخدم والـ flags (`is_platform_admin`, `is_staff`) | حصرياً لمدير المنصة ككل. |

---

> [!TIP]
> جميع نقاط النهاية المذكورة أعلاه تم بناؤها واختبارها وتدقيقها في الباك إند بنسبة 100% وهي جاهزة تماماً للربط المباشر فور بدء مرحلة الواجهات الأمامية.
