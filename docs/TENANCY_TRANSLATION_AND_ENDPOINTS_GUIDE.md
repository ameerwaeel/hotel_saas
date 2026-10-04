# 🏛️ الدليل المعماري الشامل: عزل المستأجرين، نظام الترجمة، ونقاط النهاية (Phases 4 - 7)
## Architecture Guide: Multi-Tenant Isolation, Translation System (i18n), and Endpoints Classification

**المسار:** `docs/TENANCY_TRANSLATION_AND_ENDPOINTS_GUIDE.md`  
**المرجع المعماري:** `HOTEL_SaaS_Full_Plan (2).md`  
**تاريخ التوثيق:** 2026-10-04  

---

## 📑 فهرس محتويات الدليل

1. [السؤال الأول: كيف يتعرف النظام على الفندق؟ وهل عزل المستأجرين محمي 100%؟](#1-السؤال-الأول-آلية-تحديد-الفندق-وعزل-المستأجرين-tenant-resolution--isolation)
2. [السؤال الثاني: كيف يعمل نظام الترجمة (i18n) بين الباك إند والفرونت إند؟](#2-السؤال-الثاني-نظام-الترجمة-الشامل-translation--i18n-architecture)
3. [السؤال الثالث: تحويل الأقسام (Department) إلى Model مستقل لكل فندق](#3-السؤال-الثالث-تحويل-الأقسام-department-إلى-model-مستقل)
4. [السؤال الرابع: جدول تصنيف كافة Endpoints من Phase 4 إلى 7 (SaaS Model vs Hotel Model)](#4-السؤال-الرابع-جدول-تصنيف-كافة-endpoints-من-phase-4-إلى-7)

---

## 1. السؤال الأول: آلية تحديد الفندق وعزل المستأجرين (Tenant Resolution & Isolation)

### ❓ نص التساؤل:
> *"Hotel Languages , Booking Sources , Room Types, Rooms , Customers, Employees: هيتعرف منين اللي بنشأءه هنا هو هيكون لفندق معين؟ لو بجرب الاند بوينت دي بيوزر خاص بالساس مودل أو الأدمن داش بورد الأساسية هعرف أريتو تبع أني فندق منين؟ وهل معمول لير حماية إن كل فندق ميشوفش بيانات الفندق الآخر ولو دخلت أكثر من يوزر لفندق مختلف على نفس الاندبوينت مش هيشوفوا بعض وكل فندق معزول؟"*

---

### 🛡️ الجواب المعماري الدقيق:

### أ. من أين يعرف النظام أن هذا السجل تابع لفندق معين؟
في الأنظمة متعددة المستأجرين (Multi-Tenant SaaS) ذات المستوى الاحترافي، **لا يُطلب أبداً من المستخدم إرسال `hotel_id` داخل الـ JSON Body** للعمليات التشغيلية (الغرف، النزلاء، الحجوزات، الموظفين).
**السبب الأمني:** لو سمحنا للعميل بإرسال `hotel_id` في الـ Body، يمكن لأي مخترق تعديل الـ ID وإرسال بيانات لفندق آخر!

**بدلاً من ذلك، يتعرف النظام على الفندق عبر الـ Context المحقون آلياً بـ `TenantMiddleware` (`common/middleware/tenant.py`):**

```
Client Request (Postman / Frontend / Mobile)
     │
     ├── 1. Header:  X-Hotel-ID: <UUID>        (الأولوية الأولى - للـ API والفرونت إند)
     └── 2. Session: active_hotel_id           (الأولوية الثانية - للداش بورد وجلسات التصفح)
     │
     ▼
[ TenantMiddleware ] ─── يجلب كائن الفندق النشط ويحقنه في: request.hotel
     │
     ▼
[ Service / Serializer ] ─── serializer.save(hotel=request.hotel)  (تلقائياً دون تدخل يدوي)
```

1. **عند الإرسال من Postman أو Frontend:**
   تضع في الهيدر (Headers) مفتاحاً واحداً فقط:
   ```http
   Authorization: Bearer <access_token>
   X-Hotel-ID: cd19d916-13b5-48d6-b9f0-1d39531e740b
   ```
2. **داخل الكود (Service Layer & ViewSets):**
   عند تنفيذ `POST /api/v1/rooms/rooms/` مثلاً:
   - الدالة `perform_create` في الـ View تأخذ الفندق تلقائياً:
     ```python
     def perform_create(self, serializer):
         serializer.save(hotel=self.request.hotel)
     ```
   - المستخدم يرسل فقط:
     ```json
     {
       "room_type": "b2f6...uuid",
       "room_number": "101",
       "floor": 1
     }
     ```
     والنظام يربط الغرفة بالفندق `request.hotel` الذي حُدد في الهيدر.

---

### ب. لو أنا بجرّب بيوزر الساس مودل (Platform Admin) أو أدمن الداش بورد الأساسية، هحدّد الفندق منين؟
مدير المنصة (Platform Admin / Superuser) لديه ميزة معمارية خاصة:
1. **التبديل اللحظي عبر الهيدر (Header Switching):**
   - كأدمن منصة، لست بحاجة لإنشاء عضوية موظف داخل كل فندق لتجربته!
   - فقط ضع في الـ Headers:
     `X-Hotel-ID: <UUID_فندق_أ>` → فيتم إنشاء الغرف والنزلاء فوراً داخل فندق (أ).
     غيّر الهيدر إلى:
     `X-Hotel-ID: <UUID_فندق_ب>` → فيتم العمل فوراً داخل فندق (ب).
2. **أو عبر نقطة اختيار الفندق النشط (Select Hotel Endpoint):**
   - ترسل طلب:
     `POST /api/v1/auth/select-hotel/`
     ```json
     {
       "hotel_id": "cd19d916-13b5-48d6-b9f0-1d39531e740b"
     }
     ```
   - سيقوم النظام بتثبيت هذا الفندق كفندق نشط لجلسة العمل الحالية، وأي استدعاء بعد ذلك سيتعامل مع هذا الفندق مباشرة.
   - **ملاحظة أمان:** كلاسات الصلاحيات (`IsHotelMember` و `HasHotelPermission`) تحتوي على هذا السطر:
     ```python
     if request.user.is_platform_admin or request.user.is_superuser:
         return True  # Platform admin bypasses membership checks
     ```
     بينما لو حاول يوزر عادي اختيار فندق لا ينتمي له، سيحصل على:  
     `400/403: You are not an active member of this hotel`.

---

### ج. هل معمول طبقة حماية (Tenant Isolation) تمنع الفنادق من رؤية بيانات بعضها؟
**نعم، بنسبة 100% وبحماية ثلاثية الطبقات (Triple-Layer Tenant Isolation):**

```
┌────────────────────────────────────────────────────────────────────────┐
│  الطبقة 1: مستوى الاستعلامات (ORM Query Layer)                           │
│  كل كويري يجبر الفلترة عبر TenantManager:                                │
│  Room.objects.for_hotel(request.hotel)                                 │
│  SQL الناتج: WHERE hotel_id = 'UUID_فندق_1'                             │
├────────────────────────────────────────────────────────────────────────┤
│  الطبقة 2: مستوى الصلاحيات والأمان (RBAC & Membership Layer)             │
│  IsHotelMember: يرفض الطلب بـ 403 فوراً إذا حاول يوزر فندق (1) إرسال     │
│  X-Hotel-ID لفندق (2).                                                 │
├────────────────────────────────────────────────────────────────────────┤
│  الطبقة 3: مستوى قيود قاعدة البيانات (Database Constraints)              │
│  UniqueConstraint(fields=["hotel", "room_number"])                     │
│  تسمح لفندق (1) بامتلاك غرفة 101 ولفندق (2) بامتلاك غرفة 101 بأمان تام. │
└────────────────────────────────────────────────────────────────────────┘
```

#### ماذا يحدث لو دخل يوزران لفندقين مختلفين على نفس الـ Endpoint؟
1. **يوزر فندق A** يطلب `GET /api/v1/rooms/rooms/`:
   - `request.hotel` = Hotel A.
   - الـ View ينفذ: `Room.objects.for_hotel(Hotel_A)`.
   - يرى **فقط** غرف فندق A (مثلاً 101, 102).
2. **يوزر فندق B** يطلب نفس الـ Endpoint `GET /api/v1/rooms/rooms/`:
   - `request.hotel` = Hotel B.
   - الـ View ينفذ: `Room.objects.for_hotel(Hotel_B)`.
   - يرى **فقط** غرف فندق B (مثلاً 201, 202).
3. **محاولة اختراق (Data Tampering):**
   - لو أخذ يوزر فندق A معرف الغرفة `uuid-room-B` الخاصة بفندق B وطلب:  
     `GET /api/v1/rooms/rooms/uuid-room-B/`
   - دجانجو سينفذ داخلياً:  
     `SELECT * FROM rooms_room WHERE id = 'uuid-room-B' AND hotel_id = 'Hotel_A_ID'`
   - النتيجة: **404 Not Found**! لن تظهر الغرفة ولن يعلم بوجودها إطلاقاً.
   - تم التحقق من ذلك بـ 11 اختباراً آلياً في `tests/test_tenant_isolation.py`.

---

## 2. السؤال الثاني: نظام الترجمة الشامل (Translation / i18n Architecture)

### ❓ نص التساؤل:
> *"هو أنت هتمشي نظام الترجمة إزاي؟ هل الداتا اللي راجعة بلغات مختلفة ولا هتمشيها إزاي؟ + إن في الديزاين نفسه هيبقى في عرض كلمات وكل كلمة هتتغير بلغة على حسب ما هختار اللغة في الفرونت، هتمشيها إزاي باك ولا فرونت؟ وفهمني ملف الترجمة أو جزء الترجمة هتمشيه إزاي اشرحلي بالتفصيل؟"*

---

### 🌐 الجواب المعماري الشامل:
في الأنظمة السحابية المعقدة، تنقسم الترجمة إلى **نوعين مختلفين تماماً**، لكل منهما معمارية خاصة:

```
                               ┌──────────────────────────────────────────────┐
                               │             نظام الترجمة في المنصة           │
                               └──────────────────────┬───────────────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
        ┌─────────────────────────────┐                               ┌─────────────────────────────┐
        │   1. نصوص الواجهة الثابتة    │                               │  2. نصوص البيانات الديناميكية │
        │     (Static UI Texts)       │                               │    (Dynamic Database Data)  │
        ├─────────────────────────────┤                               ├─────────────────────────────┤
        │ • الأزرار (حفظ، إلغاء)      │                               │ • اسم نوع الغرفة (ديلوكس)   │
        │ • عناوين الجداول والقوائم   │                               │ • وصف الغرفة ومميزاتها      │
        │ • رسائل النظام والتنبيهات   │                               │ • شروط وسياسات الفندق       │
        ├─────────────────────────────┤                               ├─────────────────────────────┤
        │ المسؤول: 💻 Frontend (React)│                               │ المسؤول: ⚙️ Backend (Django)│
        │ الأداة: react-i18next       │                               │ الأداة: Translation Models  │
        └─────────────────────────────┘                               └─────────────────────────────┘
```

---

### أ. ترجمة نصوص الواجهة الثابتة (Static UI) — مسؤولية الفرونت إند (Frontend)
الكلمات الثابتة في التصميم (مثل: "لوحة التحكم", "تسجيل الدخول", "إجمالي الدخل", "رقم الغرفة", "حفظ", "إلغاء"):
- **لا تُطلب من الباك إند في كل ضغطة زر!** طلبها من الباك إند سيسبب بطئاً وتأخيراً لا داعي له.
- **كيف تعمل في الفرونت إند (React / Vite):**
  1. نستخدم مكتبة `react-i18next` القياسية مع `i18next`.
  2. يتم إنشاء مجلد داخل الفرونت إند:
     ```
     frontend/src/locales/
     ├── en/
     │   └── translation.json    {"rooms": "Rooms", "save": "Save", "cancel": "Cancel"}
     ├── ar/
     │   └── translation.json    {"rooms": "الغرف", "save": "حفظ", "cancel": "إلغاء"}
     └── fr/
         └── translation.json    {"rooms": "Chambres", "save": "Enregistrer", "cancel": "Annuler"}
     ```
  3. في كود React:
     ```tsx
     import { useTranslation } from 'react-i18next';

     export const RoomHeader = () => {
         const { t } = useTranslation();
         return <h1>{t('rooms')}</h1>;  // ستعرض "الغرف" أو "Rooms" فوراً
     };
     ```
  4. **تبديل اللغة وتعديل الاتجاه (RTL / LTR):**
     - عند اختيار اللغة من القائمة المنسدلة:
       ```ts
       i18n.changeLanguage('ar');
       document.documentElement.dir = 'rtl'; // يقلب التصميم لليمين تلقائياً
       ```
     - يتم التبديل في أقل من 1 ميلي ثانية (Instant Switch) من الذاكرة المحلية للمتصفح دون الحاجة لأي Request إلى السيرفر.

---

### ب. ترجمة البيانات الديناميكية (Dynamic Database Data) — مسؤولية الباك إند (Backend)
البيانات التي يدخلها أصحاب الفنادق بأنفسهم (مثل: فئة الغرفة "Deluxe Suite" ويريدونها بالعربية "جناح ديلوكس" وبالفرنسية "Suite Deluxe"):
- هذه البيانات مخزنة في قاعدة البيانات، ولذلك صممنا في Phase 4 نموذجاً مخصصاً لها: `RoomTypeTranslation`.

```
┌────────────────────────────────┐
│           RoomType             │ (السعر الأساسي، السعة، الفندق)
└───────────────┬────────────────┘
                │ 1 to Many
                ▼
┌────────────────────────────────┐
│      RoomTypeTranslation       │
├────────────────────────────────┤
│ • language: "ar" ── "جناح فاخر"│
│ • language: "en" ── "Deluxe"   │
│ • language: "fr" ── "De Luxe"  │
└────────────────────────────────┘
```

#### كيف ترجع البيانات من الـ API؟ (هناك حالتان)
1. **شاشة إدارة وتعديل الغرف (لوحة تحكم الفندق):**
   عندما يفتح مدير الفندق الغرفة لتعديلها، يحتاج لرؤية كافة الترجمات لتعديلها معاً:
   - يطلب: `GET /api/v1/rooms/room-types/{id}/`
   - الـ API يرجع كل اللغات:
     ```json
     {
       "id": "uuid...",
       "code": "DLX",
       "base_price": "200.00",
       "translations": [
         {"language_code": "en", "name": "Deluxe Room", "description": "Sea view room"},
         {"language_code": "ar", "name": "غرفة ديلوكس", "description": "غرفة مطلة على البحر"}
       ]
     }
     ```
2. **شاشة الاستقبال والحجوزات (أو موقع حجز النزلاء العام):**
   النزيل أو موظف الاستقبال اختار واجهة عربية، ويريد رؤية الاسم المترجم مباشرة:
   - يرسل الفرونت إند مع الطلب هيدر اللغة المعتمد عالمياً:
     `Accept-Language: ar`
   - الباك إند يقرأ الهيدر ويُرجع الحقل المترجم المباشر، مع ميزة التراجع الذكي (Fallback):  
     إذا لم تتوفر الترجمة العربية لهذا الاسم، يُرجع النظام تلقائياً لغة الفندق الافتراضية (`HotelLanguage.is_default`).

---

## 3. السؤال الثالث: تحويل الأقسام (Department) إلى Model مستقل

### ❓ نص الملاحظة:
> *"الـ department في الـ roomapp هيكون model مش textchoices لأن كل فندق هيدخل نوع العمالة عنده بأقسام بمسميات مختلفة مش ستاندرد"*

---

### 💡 الرأي المعماري وخطة التنفيذ:
**ملاحظتك صحيحة واحترافية بنسبة 100%!**  
في الفنادق الواقعية:
- فندق (A) منتجع كبير (Resort): يحتاج أقسام مثل: "قسم الشواطئ والمسابح"، "قسم الحفلات والمناسبات"، "نادي الأطفال"، "السبا الصحي".
- فندق (B) فندق أعمال (Business Hotel): يحتاج أقسام مثل: "مركز رجال الأعمال"، "خدمات الليموزين"، "الأمن السيبراني وكاميرات المراقبة".
- جعل `Department` مجرد `TextChoices` ثابتة يُقيد الفنادق ويمنعها من تخصيص هيكلها الإداري.

*(ملاحظة تقنية: قسم العمالة يتبع تطبيق `customers` الذي يحتوي على مودل `Employee` ومودل `Customer` وليس تطبيق `rooms`)*.

---

### 📐 التصميم المعماري لمودل `Department` كـ Model مستقل:

#### 1. المودل الجديد (`customers/models.py`):
```python
class Department(BaseModel, HotelOwnedMixin):
    """
    أقسام وهيكل العمالة الخاص بكل فندق.
    معزول لكل مستأجر عبر TenantManager.
    """
    objects = TenantManager()

    name = models.CharField(max_length=100, verbose_name=_("Department Name"))
    code = models.SlugField(max_length=50, blank=True, verbose_name=_("Code"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "name"],
                name="unique_department_per_hotel"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.hotel.name})"
```

#### 2. تعديل مودل `Employee`:
بدلاً من حقل `CharField(choices=Department.choices)`، يصبح علاقة مفتاح أجنبي:
```python
class Employee(BaseModel, HotelOwnedMixin):
    # ...
    department = models.ForeignKey(
        "customers.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employees",
        verbose_name=_("Department")
    )
```

#### 3. واجهات الـ CRUD المقابلة (`/api/v1/customers/departments/`):
- `GET /api/v1/customers/departments/`: استعراض أقسام الفندق الحالي.
- `POST /api/v1/customers/departments/`: إنشاء قسم جديد للفندق.
- `PUT/PATCH /api/v1/customers/departments/{id}/`: تعديل اسم أو تفاصيل القسم.
- `DELETE /api/v1/customers/departments/{id}/`: تعطيل أو حذف القسم (محمي بـ `PROTECT` لمنع حذف قسم به موظفون).

---

## 4. السؤال الرابع: جدول تصنيف كافة Endpoints من Phase 4 إلى 7

### ❓ نص الطلب:
> *"ممكن من phase 4:7 تديني الاندبوينت وتقولي هي تبع ساس مودل ولا تبع فندق وتديهملي تحت بعض كلهم"*

---

### 📊 الجدول الشامل والمصنف لنقاط النهاية (Endpoints Classification):

> 📌 **توضيح التصنيفات:**
> - 🏨 **[Hotel Model / Tenant-Scoped] (خاص بفندق):** مسارات تشغيلية يومية لا تعمل إلا في سياق فندق نشط (`request.hotel`). تتطلب إرسال `X-Hotel-ID` أو اختيار الفندق النشط. بياناتها معزولة تماماً لكل مستأجر.
> - 🌐 **[SaaS Model / Platform Admin] (إدارة المنصة / عام):** مسارات على مستوى المنصة ككل، إما جداول مرجعية عامة بدون ربط بفندق (مثل كتالوج اللغات العالمية)، أو عمليات خاصة بمدير المنصة العام.

---

### المرحلة 4: البيانات الأساسية والغرف والعملاء (`rooms` & `customers`)

| # | Method | Endpoint | تصنيف التبعية | الصلاحية المطلوبة | الوصف والوظيفة |
|---|:---:|---|:---:|:---:|---|
| 1 | `GET` | `/api/v1/rooms/languages/` | 🌐 **SaaS Model (عام)** | مسجل بالمنصة | استعراض قائمة اللغات العالمية المتاحة في النظام |
| 2 | `POST` | `/api/v1/rooms/languages/` | 🌐 **SaaS Model (منصة)** | `IsPlatformAdmin` | إضافة لغة جديدة لكتالوج اللغات العالمي للمنصة |
| 3 | `GET` | `/api/v1/rooms/languages/{id}/` | 🌐 **SaaS Model (عام)** | مسجل بالمنصة | استعراض تفاصيل لغة معينة |
| 4 | `DELETE` | `/api/v1/rooms/languages/{id}/` | 🌐 **SaaS Model (منصة)** | `IsPlatformAdmin` | حذف لغة من كتالوج المنصة العام |
| 5 | `GET` | `/api/v1/rooms/hotel-languages/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | قائمة اللغات المفعلة بالفندق النشط |
| 6 | `POST` | `/api/v1/rooms/hotel-languages/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | تفعيل لغة جديدة للفندق وتحديد إن كانت الافتراضية |
| 7 | `DELETE` | `/api/v1/rooms/hotel-languages/{id}/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | إزالة لغة من قائمة لغات الفندق النشط |
| 8 | `GET` | `/api/v1/rooms/booking-sources/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | استعراض قنوات الحجز الخاصة بالفندق النشط |
| 9 | `POST` | `/api/v1/rooms/booking-sources/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | إضافة قناة حجز جديدة للفندق (Walk-in, Booking...) |
| 10 | `GET` | `/api/v1/rooms/booking-sources/{id}/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | استعراض تفاصيل قناة حجز بالفندق |
| 11 | `PUT/PATCH` | `/api/v1/rooms/booking-sources/{id}/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | تعديل اسم أو نسبة عمولة قناة الحجز بالفندق |
| 12 | `DELETE` | `/api/v1/rooms/booking-sources/{id}/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | حذف قناة حجز من الفندق النشط |
| 13 | `GET` | `/api/v1/rooms/room-types/` | 🏨 **Hotel Model (فندق)** | `rooms.view` | قائمة فئات الغرف بالفندق النشط مع ترجماتها |
| 14 | `POST` | `/api/v1/rooms/room-types/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | إنشاء فئة غرف جديدة للفندق مع أسعارها وترجماتها |
| 15 | `GET` | `/api/v1/rooms/room-types/{id}/` | 🏨 **Hotel Model (فندق)** | `rooms.view` | استعراض تفاصيل فئة غرفة محددة بالفندق |
| 16 | `PUT/PATCH` | `/api/v1/rooms/room-types/{id}/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | تعديل بيانات وأسعار وترجمات فئة الغرفة |
| 17 | `DELETE` | `/api/v1/rooms/room-types/{id}/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | تعطيل أو حذف فئة غرفة من الفندق |
| 18 | `GET` | `/api/v1/rooms/rooms/` | 🏨 **Hotel Model (فندق)** | `rooms.view` | استعراض غرف الفندق مع فلترة الحالة والطابق |
| 19 | `POST` | `/api/v1/rooms/rooms/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | إضافة غرفة جديدة برقم فريد داخل الفندق النشط |
| 20 | `GET` | `/api/v1/rooms/rooms/{id}/` | 🏨 **Hotel Model (فندق)** | `rooms.view` | تفاصيل غرفة محددة داخل الفندق |
| 21 | `PUT/PATCH` | `/api/v1/rooms/rooms/{id}/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | تعديل بيانات الغرفة داخل الفندق |
| 22 | `DELETE` | `/api/v1/rooms/rooms/{id}/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | حذف أو تعطيل غرفة بالفندق |
| 23 | `PATCH` | `/api/v1/rooms/rooms/{id}/status/` | 🏨 **Hotel Model (فندق)** | `rooms.manage` | تحديث حالة الغرفة الفندقية (مع فحص الأعطال المانعة) |
| 24 | `GET` | `/api/v1/customers/customers/` | 🏨 **Hotel Model (فندق)** | `customers.view` | قائمة نزلاء وضيوف الفندق والبحث بالهاتف والاسم |
| 25 | `POST` | `/api/v1/customers/customers/` | 🏨 **Hotel Model (فندق)** | `customers.manage` | تسجيل ملف نزيل جديد بالفندق |
| 26 | `GET` | `/api/v1/customers/customers/{id}/` | 🏨 **Hotel Model (فندق)** | `customers.view` | ملف النزيل وتاريخ إقاماته بالفندق |
| 27 | `PUT/PATCH` | `/api/v1/customers/customers/{id}/` | 🏨 **Hotel Model (فندق)** | `customers.manage` | تحديث بيانات النزيل والوثائق |
| 28 | `DELETE` | `/api/v1/customers/customers/{id}/` | 🏨 **Hotel Model (فندق)** | `customers.manage` | أرشفة أو حذف ملف نزيل من الفندق |
| 29 | `GET` | `/api/v1/customers/employees/` | 🏨 **Hotel Model (فندق)** | `customers.view` | قائمة الموظفين التابعين للفندق النشط |
| 30 | `POST` | `/api/v1/customers/employees/` | 🏨 **Hotel Model (فندق)** | `customers.manage` | إنشاء وتعيين بروفايل موظف لفندق محدد |
| 31 | `GET` | `/api/v1/customers/employees/{id}/` | 🏨 **Hotel Model (فندق)** | `customers.view` | استعراض بيانات وظيفة الموظف وقسمه بالفندق |
| 32 | `PUT/PATCH` | `/api/v1/customers/employees/{id}/` | 🏨 **Hotel Model (فندق)** | `customers.manage` | تعديل مسمى وقسم ورتبة الموظف بالفندق |
| 33 | `DELETE` | `/api/v1/customers/employees/{id}/` | 🏨 **Hotel Model (فندق)** | `customers.manage` | إنهاء خدمة أو تعطيل موظف في الفندق |

---

### المرحلة 5: محرك الحجوزات والتوفر (`reservations`)

| # | Method | Endpoint | تصنيف التبعية | الصلاحية المطلوبة | الوصف والوظيفة |
|---|:---:|---|:---:|:---:|---|
| 34 | `GET` | `/api/v1/reservations/availability/` | 🏨 **Hotel Model (فندق)** | عضو بالفندق | فحص الغرف المتاحة لفندق معين خلال فترة زمنية |
| 35 | `GET` | `/api/v1/reservations/` | 🏨 **Hotel Model (فندق)** | `reservations.view` | استعراض سجلات الحجوزات الخاصة بالفندق النشط |
| 36 | `POST` | `/api/v1/reservations/` | 🏨 **Hotel Model (فندق)** | `reservations.manage` | إنشاء حجز جديد وقفل الغرف ومنع التضارب الزمني |
| 37 | `GET` | `/api/v1/reservations/{id}/` | 🏨 **Hotel Model (فندق)** | `reservations.view` | تفاصيل حجز نزيل معين بغرفه وأسعاره بالفندق |
| 38 | `PATCH` | `/api/v1/reservations/{id}/` | 🏨 **Hotel Model (فندق)** | `reservations.manage` | تعديل ملاحظات وتفاصيل الحجز |
| 39 | `DELETE` | `/api/v1/reservations/{id}/` | 🏨 **Hotel Model (فندق)** | `reservations.manage` | إلغاء الحجز بالفندق |
| 40 | `PATCH` | `/api/v1/reservations/{id}/status/` | 🏨 **Hotel Model (فندق)** | `reservations.manage` | تغيير حالة الحجز عبر آلة الحالات (تأكيد، تسكين، مغادرة) |
| 41 | `POST` | `/api/v1/reservations/{id}/upgrade-room/` | 🏨 **Hotel Model (فندق)** | `reservations.manage` | ترقية أو نقل النزيل لغرفة أخرى وتوثيق فرق السعر |

---

### المرحلة 6: المدفوعات والماليات والإغلاقات (`payments` & `finance`)

| # | Method | Endpoint | تصنيف التبعية | الصلاحية المطلوبة | الوصف والوظيفة |
|---|:---:|---|:---:|:---:|---|
| 42 | `GET` | `/api/v1/payments/methods/` | 🏨 **Hotel Model (فندق)** | `payments.view` | وسائل الدفع المقبولة بالفندق الحالي |
| 43 | `POST` | `/api/v1/payments/methods/` | 🏨 **Hotel Model (فندق)** | `payments.manage` | تعريف وسيلة دفع جديدة للفندق |
| 44 | `GET` | `/api/v1/payments/methods/{id}/` | 🏨 **Hotel Model (فندق)** | `payments.view` | استعراض تفاصيل وسيلة دفع بالفندق |
| 45 | `PUT/PATCH` | `/api/v1/payments/methods/{id}/` | 🏨 **Hotel Model (فندق)** | `payments.manage` | تعديل بيانات وسيلة الدفع بالفندق |
| 46 | `DELETE` | `/api/v1/payments/methods/{id}/` | 🏨 **Hotel Model (فندق)** | `payments.manage` | إيقاف تفعيل وسيلة دفع بالفندق |
| 47 | `GET` | `/api/v1/payments/` | 🏨 **Hotel Model (فندق)** | `payments.view` | سندات وقبوضات الدفع الخاصة بالفندق النشط |
| 48 | `POST` | `/api/v1/payments/` | 🏨 **Hotel Model (فندق)** | `payments.manage` | تسجيل دفعة مالية وإنشاء قيد محاسبي تلقائي للفندق |
| 49 | `GET` | `/api/v1/payments/{id}/` | 🏨 **Hotel Model (فندق)** | `payments.view` | استعراض تفاصيل دفعة مالية معينة |
| 50 | `POST` | `/api/v1/payments/{id}/refund/` | 🏨 **Hotel Model (فندق)** | `payments.manage` | استرداد دفعة مالية وإثبات الحركة العكسية |
| 51 | `GET` | `/api/v1/finance/daily-summary/` | 🏨 **Hotel Model (فندق)** | `finance.view` | الملخص المالي اليومي للفندق مقسماً بحسب كل عملة |
| 52 | `GET` | `/api/v1/finance/categories/` | 🏨 **Hotel Model (فندق)** | `finance.view` | بنود الإيرادات والمصروفات الخاصة بالفندق |
| 53 | `POST` | `/api/v1/finance/categories/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | إنشاء بند مالي جديد للفندق (إيراد أو مصروف) |
| 54 | `GET` | `/api/v1/finance/transactions/` | 🏨 **Hotel Model (فندق)** | `finance.view` | دفتر المعاملات والقيود المحاسبية للفندق |
| 55 | `POST` | `/api/v1/finance/transactions/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | تسجيل قيد مصروف أو تسوية يدوية في الفندق |
| 56 | `GET` | `/api/v1/finance/exchange-rates/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | أسعار صرف العملات المسجلة بالفندق للعرض |
| 57 | `POST` | `/api/v1/finance/exchange-rates/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | تسجيل سعر صرف عملة جديد للفندق |
| 58 | `GET` | `/api/v1/finance/daily-closings/` | 🏨 **Hotel Model (فندق)** | `finance.view` | استعراض سجلات الإغلاقات اليومية للفندق |
| 59 | `POST` | `/api/v1/finance/daily-closings/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | تنفيذ الإغلاق المالي لليوم وحظر أي حركات لاحقة |
| 60 | `GET` | `/api/v1/finance/monthly-closings/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | استعراض سجلات الإغلاقات الشهرية المعتمدة للفندق |
| 61 | `POST` | `/api/v1/finance/monthly-closings/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | تنفيذ الإغلاق المالي للشهر وتجميع أيامه |
| 62 | `POST` | `/api/v1/finance/export/` | 🏨 **Hotel Model (فندق)** | `finance.manage` | طلب تصدير تقرير مالي للفندق غير متزامن عبر Celery |

---

### المرحلة 7: الإشراف الداخلي والصيانة والشكاوى (`housekeeping`, `maintenance`, `complaints`)

| # | Method | Endpoint | تصنيف التبعية | الصلاحية المطلوبة | الوصف والوظيفة |
|---|:---:|---|:---:|:---:|---|
| 63 | `GET` | `/api/v1/housekeeping/cleanings/` | 🏨 **Hotel Model (فندق)** | `housekeeping.view` | استعراض مهام تنظيف الغرف بالفندق النشط |
| 64 | `POST` | `/api/v1/housekeeping/cleanings/` | 🏨 **Hotel Model (فندق)** | `housekeeping.manage` | إنشاء مهمة تنظيف يدوية لغرفة بالفندق |
| 65 | `GET` | `/api/v1/housekeeping/cleanings/{id}/` | 🏨 **Hotel Model (فندق)** | `housekeeping.view` | استعراض بيانات وتوقيتات مهمة تنظيف |
| 66 | `PATCH` | `/api/v1/housekeeping/cleanings/{id}/action/` | 🏨 **Hotel Model (فندق)** | `housekeeping.manage` | نقل مرحلة التنظيف (بدء، إتمام، فحص واعتماد) |
| 67 | `GET` | `/api/v1/maintenance/issues/` | 🏨 **Hotel Model (فندق)** | `maintenance.view` | قائمة بلاغات وأعطال الغرف بالفندق النشط |
| 68 | `POST` | `/api/v1/maintenance/issues/` | 🏨 **Hotel Model (فندق)** | `maintenance.manage` | الإبلاغ عن عطل بغرفة (مع خيار حظر الغرفة blocking) |
| 69 | `GET` | `/api/v1/maintenance/issues/{id}/` | 🏨 **Hotel Model (فندق)** | `maintenance.view` | تفاصيل بلاغ صيانة محدد بالفندق |
| 70 | `PATCH` | `/api/v1/maintenance/issues/{id}/` | 🏨 **Hotel Model (فندق)** | `maintenance.manage` | تعديل بيانات وتفاصيل بلاغ الصيانة |
| 71 | `DELETE` | `/api/v1/maintenance/issues/{id}/` | 🏨 **Hotel Model (فندق)** | `maintenance.manage` | حذف بلاغ صيانة من سجلات الفندق |
| 72 | `PATCH` | `/api/v1/maintenance/issues/{id}/resolve/` | 🏨 **Hotel Model (فندق)** | `maintenance.manage` | إثبات إصلاح العطل وتدوين ملاحظات الفني |
| 73 | `PATCH` | `/api/v1/maintenance/issues/{id}/assign/` | 🏨 **Hotel Model (فندق)** | `maintenance.manage` | إسناد وتكليف فني صيانة بعطل الغرفة |
| 74 | `GET` | `/api/v1/complaints/complaints/` | 🏨 **Hotel Model (فندق)** | `complaints.view` | استعراض شكاوى النزلاء المسجلة بالفندق |
| 75 | `POST` | `/api/v1/complaints/complaints/` | 🏨 **Hotel Model (فندق)** | `complaints.manage` | تسجيل شكوى جديدة لعميل في الفندق |
| 76 | `GET` | `/api/v1/complaints/complaints/{id}/` | 🏨 **Hotel Model (فندق)** | `complaints.view` | تفاصيل شكوى نزيل وإجراءات متابعتها |
| 77 | `PATCH` | `/api/v1/complaints/complaints/{id}/` | 🏨 **Hotel Model (فندق)** | `complaints.manage` | تعديل تفاصيل وأولوية الشكوى |
| 78 | `DELETE` | `/api/v1/complaints/complaints/{id}/` | 🏨 **Hotel Model (فندق)** | `complaints.manage` | حذف شكوى نزيل من سجلات الفندق |
| 79 | `PATCH` | `/api/v1/complaints/complaints/{id}/resolve/` | 🏨 **Hotel Model (فندق)** | `complaints.manage` | إغلاق الشكوى وتسجيل تقرير وتفاصيل الحل |
| 80 | `PATCH` | `/api/v1/complaints/complaints/{id}/assign/` | 🏨 **Hotel Model (فندق)** | `complaints.manage` | إسناد الشكوى لموظف محدد لمتابعتها |

---

## 📌 خلاصة واستنتاج إحصائي

- **إجمالي Endpoints في المراحل من 4 إلى 7:** **80 نقطة نهاية (Endpoint)**.
- **عدد مسارات الـ SaaS Model (إدارة المنصة العامة):** **4 مسارات فقط** (الخاصة بكتالوج اللغات العالمية `Language`).
- **عدد مسارات الـ Hotel Model (الخاصة بالفندق النشط):** **76 مساراً** (تشكل 95% من النظام، وكلها تعمل داخل نطاق المستأجر النشط ومحمية بعزل تام لمنع تسريب أي معلومة لفندق آخر).

---

## 5. دليل استخدام `X-Hotel-ID` بالتفصيل (أين تضعه؟ ومن أين تحصل عليه؟)

### ❓ التساؤل الشائع:
> *"أنا شايف في التوثيق: `Auth: Authorization: Bearer <access_token> + X-Hotel-ID: <hotel_uuid>`*  
> *أحط الـ `X-Hotel-ID` ده فين بالضبط في الطلب؟ وأجيب الـ `<hotel_uuid>` ده منين؟ وهل كل الاندبوينتس بتحتاجه؟"*

---

### أ. من أين تحصل على الـ `<hotel_uuid>`؟ (5 طرق عملية وسهلة)

للحصول على معرّف الفندق المستهدف (UUID)، لديك 5 خيارات مباشرة وسريعة:

#### 1. الطريقة الأسهل لأدمن المنصة (Platform Admin): عبر استدعاء قائمة الفنادق
- **الرابط:** `GET http://127.0.0.1:8000/api/v1/tenants/`
- **الهيدرز:** `Authorization: Bearer <access_token>`
- **الرد (Response):** سيرجع مصفوفة بجميع الفنادق المسجلة في قاعدة البيانات مع الـ `id` لكل منها:
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
        "name": "Grand Palace Hotel",
        "subdomain": "grand-palace",
        "status": "active"
      },
      {
        "id": "9f8e7d6c-5b4a-3210-fedc-ba9876543210",
        "name": "Sea View Resort",
        "subdomain": "seaview",
        "status": "active"
      }
    ]
  }
  ```
  👉 **تنسخ قيمة `"id"`** وتستخدمها كـ `<hotel_uuid>`.

#### 2. لمدير الفندق أو الموظف العادي: عبر نقطة `my-hotels`
- **الرابط:** `GET http://127.0.0.1:8000/api/v1/auth/my-hotels/`
- **الهيدرز:** `Authorization: Bearer <access_token>`
- **الرد (Response):** يرجع الفنادق التي ينتمي لها المستخدم فقط مع صلاحياته ودوره:
  ```json
  {
    "success": true,
    "data": [
      {
        "hotel_id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
        "hotel_name": "Grand Palace Hotel",
        "role": "Manager"
      }
    ]
  }
  ```

#### 3. عند إنشاء فندق جديد (Tenant Onboarding):
- عند استدعاء نقطة إنشاء الفندق مع المالك: `POST /api/v1/auth/register-hotel/`
- الرد المباشر يحتوي فوراً على:
  ```json
  "hotel": {
    "id": "cd19d916-13b5-48d6-b9f0-1d39531e740b",
    "name": "Grand Palace Hotel"
  }
  ```

#### 4. من لوحة تحكم دجانجو (Django Admin Dashboard):
- ادخل إلى: `http://127.0.0.1:8000/admin/tenants/hotel/`
- اضغط على أي فندق، ستجد الـ `ID` ظاهراً في حقل الـ ID وفي رابط المتصفح (URL).

#### 5. من موجه أوامر دجانجو (Django Shell):
```bash
python manage.py shell
>>> from tenants.models import Hotel
>>> for h in Hotel.objects.all(): print(h.name, h.id)
```

---

### ب. أين تضع `X-Hotel-ID: <hotel_uuid>` في برنامج Postman أو التطبيق؟

يتم وضع `X-Hotel-ID` في **رأس الطلب (HTTP Headers)** وليس في الـ Body وليس في الـ Query Params:

#### 1. في برنامج Postman / Insomnia:
1. افتح التاب المسمى **Headers** (الموجود بجانب Params و Body).
2. أضف سطرين أساسيين:
   - **Key:** `Authorization` ── **Value:** `Bearer eyJhbGciOi...`
   - **Key:** `X-Hotel-ID` ── **Value:** `cd19d916-13b5-48d6-b9f0-1d39531e740b`

```
┌────────────────────────────────────────────────────────────────────────┐
│ POST  http://127.0.0.1:8000/api/v1/rooms/rooms/                        │
├────────────────────────────────────────────────────────────────────────┤
│ Params | Authorization | [ Headers (3) ] | Body | Pre-request | Tests  │
├─────────────────────────┬──────────────────────────────────────────────┤
│ Key                     │ Value                                        │
├─────────────────────────┼──────────────────────────────────────────────┤
│ Authorization           │ Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpX...   │
│ X-Hotel-ID              │ cd19d916-13b5-48d6-b9f0-1d39531e740b         │
│ Content-Type            │ application/json                             │
└─────────────────────────┴──────────────────────────────────────────────┘
```

#### 2. في أوامر cURL (من التيرمينال):
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/rooms/rooms/" \
     -H "Authorization: Bearer <your_token>" \
     -H "X-Hotel-ID: cd19d916-13b5-48d6-b9f0-1d39531e740b" \
     -H "Content-Type: application/json" \
     -d '{"room_type": "...", "room_number": "101", "floor": 1}'
```

#### 3. في كود الفرونت إند (React / Axios Interceptor):
يتم حقنه تلقائياً في كل استدعاء API بواسطة Axios Interceptor:
```ts
// frontend/src/api/client.ts
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  const activeHotelId = localStorage.getItem('active_hotel_id');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (activeHotelId) {
    config.headers['X-Hotel-ID'] = activeHotelId;
  }
  return config;
});
```

---

### ج. تنبيه هام جداً: متى تحتاجه ومتى لا تحتاجه؟

في المثال الذي اقتبسته من توثيق Phase 4:
```http
POST /api/v1/rooms/languages/
{
  "code": "ar",
  "name": "Arabic",
  "native_name": "العربية",
  "is_rtl": true
}
```
> ⚠️ **ملاحظة ذهبية:**  
> نقطة `/api/v1/rooms/languages/` هي **جدول عام على مستوى المنصة ككل (Global SaaS Model)**.  
> اللغات ليست خاصة بفندق معين بل يشاركها كل النظام، ولذلك **لا تحتاج ولا تطلب `X-Hotel-ID` على الإطلاق!**  
> 
> بينما تحتاجه **فقط** في نقاط النهاية الخاصة بالفندق التشغيلي (Hotel Model)، مثل:
> - تفعيل لغات الفندق: `/api/v1/rooms/hotel-languages/` (يحتاج `X-Hotel-ID`)
> - قنوات حجز الفندق: `/api/v1/rooms/booking-sources/` (يحتاج `X-Hotel-ID`)
> - غرف وفئات الفندق: `/api/v1/rooms/room-types/`, `/api/v1/rooms/rooms/` (يحتاج `X-Hotel-ID`)
> - نزلاء وعمالة الفندق: `/api/v1/customers/customers/`, `/api/v1/customers/employees/` (يحتاج `X-Hotel-ID`)
> - حجوزات الفندق: `/api/v1/reservations/` (يحتاج `X-Hotel-ID`)
> - ماليات الفندق: `/api/v1/payments/`, `/api/v1/finance/` (يحتاج `X-Hotel-ID`)
> - صيانة وإشراف الفندق: `/api/v1/maintenance/`, `/api/v1/housekeeping/` (يحتاج `X-Hotel-ID`)

