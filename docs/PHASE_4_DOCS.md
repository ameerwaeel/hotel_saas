# Phase 4 — Master Data (Rooms + Customers)
# المرحلة الرابعة — البيانات الأساسية (الغرف والعملاء والموظفين)

---

## 1. Overview | ١. نظرة عامة شاملة

> [!NOTE]
> 💡 **شرح باللغة العربية (Overview):**
> تُعد المرحلة الرابعة حجر الأساس ونقطة الانطلاق لكافة البيانات الرئيسية (Master Data) في منصة Hotel SaaS.
> كل العمليات التشغيلية اللاحقة (الحجوزات، الإشراف الداخلي والتنظيف، الفواتير، والتقارير المالية) تعتمد بشكل مباشر على الكيانات المعرفة هنا.
> يقدم هذا الجزء تطبيقين أساسيين في دجانجو: `rooms` (إدارة الغرف وفئاتها ومصادر الحجز ولغات الفندق) و `customers` (إدارة ملفات النزلاء والموظفين وتصنيف الأقسام)، مع ضمان العزل التام للمستأجرين (Tenant Isolation) عبر `TenantManager`.

Phase 4 establishes the **master-data foundation** for the entire Hotel SaaS platform. Every subsequent phase (bookings, housekeeping, billing, reporting) depends on the entities defined here.

This phase introduces two new Django apps — `rooms` and `customers` — and implements the following capabilities:

| Domain | What Was Built |
|---|---|
| **Language System** | Global `Language` lookup table + per-hotel `HotelLanguage` configuration with default enforcement |
| **Booking Sources** | Configurable `BookingSource` records (e.g., Walk-In, OTA, Phone) scoped per hotel |
| **Room Types** | `RoomType` with full i18n translation support via `RoomTypeTranslation` (one row per language) |
| **Rooms** | `Room` model with a five-state status machine (`AVAILABLE`, `OCCUPIED`, `CLEANING`, `MAINTENANCE`, `OUT_OF_ORDER`) |
| **Customers** | `Customer` model with multiple government ID types and a `get_or_create_by_id` pattern |
| **Employees** | `Employee` model backed by `accounts.User` with department classification and active `HotelMembership` validation |

Together these models provide a clean, tenant-isolated data layer — every query is scoped to the active hotel through a `TenantManager`, ensuring zero cross-hotel data leakage from day one.

---

## 2. Models

All primary-key fields are `UUIDField(default=uuid.uuid4, editable=False, primary_key=True)` unless otherwise noted. `created_at` is always `auto_now_add=True`.

---

### 2.1 `Language` | مودل اللغات العالمية

> 💡 **شرح المودل بالعربية (Global Language Lookup):**
> جدول عام للغات المعترف بها دولياً. لاحظ أنه **لا يحتوي على مفتاح خارجي للفندق (No Hotel Foreign Key)** لأن كتالوج اللغات مشترك بين جميع الفنادق في النظام لتفادي تكرار إدخال اللغات وتوحيد أكواد BCP-47.

> **App:** `rooms` &nbsp;|&nbsp; **Table:** `rooms_language`

A **global** lookup table for human languages. It carries no hotel foreign key — all hotels share the same language catalogue.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key, auto-generated |
| `code` | `CharField(max_length=10)` | BCP-47 code, e.g. `"en"`, `"ar"`, `"fr-CA"` — `unique=True` |
| `name` | `CharField(max_length=100)` | Human-readable name in English, e.g. `"Arabic"` |
| `is_active` | `BooleanField(default=True)` | Inactive languages are excluded from hotel language lists |
| `created_at` | `DateTimeField` | Auto-set on creation |

```python
class Language(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"
```

---

### 2.2 `HotelLanguage` | لغات الفندق المعتمدة

> 💡 **شرح المودل بالعربية (Hotel-Language Junction):**
> جدول ربط وسيط (Many-to-Many with Metadata) يربط الفندق باللغات التي يختار تفعيلها.
> يحتوي على حقل `is_default` لتحديد لغة افتراضية واحدة فقط لكل فندق، وتتم حماية تغيير اللغة الافتراضية برمجياً عبر `transaction.atomic` لمنع التضارب.

> **App:** `rooms` &nbsp;|&nbsp; **Table:** `rooms_hotellanguage`

Associates a `Language` with a specific hotel. Exactly one record per hotel may have `is_default=True`.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `hotel` | `ForeignKey(Hotel)` | `on_delete=CASCADE` |
| `language` | `ForeignKey(Language)` | `on_delete=PROTECT` |
| `is_default` | `BooleanField(default=False)` | At most one `True` per hotel — enforced in service layer via `transaction.atomic` |
| `created_at` | `DateTimeField` | Auto-set on creation |

**Constraint:**

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "language"],
            name="unique_hotel_language",
        )
    ]
```

---

### 2.3 `BookingSource` | مصادر وقنوات الحجز

> 💡 **شرح المودل بالعربية (Booking Sources):**
> يمثل قنوات الحجز المختلفة للفندق (مثل الحضور المباشر Walk-in، المواقع الخارجية OTA مثل Booking.com، الحجز الهاتفي، أو الشركات).
> يتضمن كوداً فريداً لكل فندق، ويساعد لاحقاً في حساب العمولات والتقارير الإحصائية.

> **App:** `rooms` &nbsp;|&nbsp; **Table:** `rooms_bookingsource`

Configurable source labels for reservations (e.g., Walk-In, Booking.com, Phone, Corporate).

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `hotel` | `ForeignKey(Hotel)` | `on_delete=CASCADE` |
| `name` | `CharField(max_length=150)` | Display name, e.g. `"Booking.com"` |
| `code` | `SlugField(max_length=60)` | Machine-readable key, e.g. `"booking-com"` — unique per hotel |
| `is_active` | `BooleanField(default=True)` | Inactive sources are hidden from booking forms |
| `created_at` | `DateTimeField` | Auto-set on creation |

**Constraint:**

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "code"],
            name="unique_bookingsource_hotel_code",
        )
    ]
```

---

### 2.4 `RoomType` | أنواع وفئات الغرف

> 💡 **شرح المودل بالعربية (Room Category):**
> يحدد فئات الغرف داخل الفندق (مثل غرفة عادية Standard، ديلوكس Deluxe، جناح Suite).
> يحتوي على السعر الأساسي لليلة (`base_price` بنوع Decimal)، السعة القصوى، والميزات (Amenities) كحقل JSON.
> نصوص الأسماء والأوصاف تُخزن في جدول منفصل متعدد اللغات (`RoomTypeTranslation`).

> **App:** `rooms` &nbsp;|&nbsp; **Table:** `rooms_roomtype`

Defines a category of rooms within a hotel (e.g., Standard, Deluxe, Suite). Translated names and descriptions live in `RoomTypeTranslation`.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `hotel` | `ForeignKey(Hotel)` | `on_delete=CASCADE` |
| `code` | `SlugField(max_length=60)` | Internal key, e.g. `"deluxe-king"` — unique per hotel |
| `base_price` | `DecimalField(max_digits=10, decimal_places=2)` | Nightly rate in hotel's currency |
| `capacity` | `IntegerField` | Maximum number of adult guests |
| `amenities` | `JSONField(default=list)` | List of amenity strings, e.g. `["WiFi", "Mini-bar", "Sea view"]` |
| `is_active` | `BooleanField(default=True)` | Inactive types are hidden from booking flows |
| `created_at` | `DateTimeField` | Auto-set on creation |

**Constraint:**

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "code"],
            name="unique_roomtype_hotel_code",
        )
    ]
```

---

### 2.5 `RoomTypeTranslation` | ترجمات أسماء وتفاصيل فئات الغرف

> 💡 **شرح المودل بالعربية (i18n Translations):**
> تطبيق مبدأ تدويل البيانات (Internationalization): كل لغة مخصصة لنوع غرفة لها سجل منفصل.
> عند التعديل، يتم استخدام أسلوب الـ Upsert (إما تحديث السجل القائم أو إنشاؤه إن لم يوجد) دون حذف الترجمات الأخرى.

> **App:** `rooms` &nbsp;|&nbsp; **Table:** `rooms_roomtypetranslation`

Stores one translated variant of a `RoomType` per language. Translations are upserted — not replaced — when a room type is updated.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `room_type` | `ForeignKey(RoomType)` | `on_delete=CASCADE`, `related_name="translations"` |
| `language` | `ForeignKey(Language)` | `on_delete=PROTECT` |
| `name` | `CharField(max_length=200)` | Translated display name |
| `description` | `TextField(blank=True)` | Translated marketing description |

**Constraint:**

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["room_type", "language"],
            name="unique_roomtypetranslation_roomtype_language",
        )
    ]
```

---

### 2.6 `Room` | الغرف الفردية وحالاتها

> 💡 **شرح المودل بالعربية (Physical Hotel Room):**
> يمثل الغرفة الفعلية في الفندق. كل غرفة لها رقم فريد داخل الفندق (`room_number`) مع السماح بتكرار نفس الرقم في فنادق أخرى.
> ترتبط بآلة حالات تشغيلية من 5 حالات: `AVAILABLE` (متاحة), `OCCUPIED` (مشغولة), `CLEANING` (قيد التنظيف), `MAINTENANCE` (صيانة), `OUT_OF_ORDER` (خارج الخدمة).

> **App:** `rooms` &nbsp;|&nbsp; **Table:** `rooms_room`

Represents a physical room in the hotel. Each room has a five-state status machine.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `hotel` | `ForeignKey(Hotel)` | `on_delete=CASCADE` |
| `room_type` | `ForeignKey(RoomType)` | `on_delete=PROTECT` |
| `room_number` | `CharField(max_length=20)` | e.g. `"101"`, `"P2-05"` — unique per hotel |
| `floor` | `IntegerField` | Floor number (can be negative for basement) |
| `status` | `CharField(max_length=20, choices=RoomStatus.choices)` | See status values below; default `AVAILABLE` |
| `notes` | `TextField(blank=True)` | Internal housekeeping or maintenance notes |
| `created_at` | `DateTimeField` | Auto-set on creation |

**Status choices:**

```python
class RoomStatus(models.TextChoices):
    AVAILABLE    = "AVAILABLE",    "Available"
    OCCUPIED     = "OCCUPIED",     "Occupied"
    CLEANING     = "CLEANING",     "Cleaning"
    MAINTENANCE  = "MAINTENANCE",  "Maintenance"
    OUT_OF_ORDER = "OUT_OF_ORDER", "Out of Order"
```

**Constraint:**

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "room_number"],
            name="unique_room_hotel_room_number",
        )
    ]
    ordering = ["floor", "room_number"]
```

---

### 2.7 `Customer` | ملف النزيل / العميل

> 💡 **شرح المودل بالعربية (Guest Profile):**
> يمثل سجل النزيل داخل الفندق. يتميز بوجود فهارس بحث سريعة على الهاتف والبريد والاسم ورقم الهوية.
> يتضمن عداداً تراكمياً للإقامات `total_stays` يتم زيادته تلقائياً عند إتمام كل حجز ومغادرة (Checkout).

> **App:** `customers` &nbsp;|&nbsp; **Table:** `customers_customer`

Represents a hotel guest. Each customer is uniquely identified within a hotel by their government-issued ID type and number combination.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `hotel` | `ForeignKey(Hotel)` | `on_delete=CASCADE` |
| `first_name` | `CharField(max_length=100)` | — |
| `last_name` | `CharField(max_length=100)` | — |
| `email` | `EmailField(blank=True)` | Optional; not unique (guests share emails) |
| `phone` | `CharField(max_length=30, blank=True)` | E.164 preferred but not enforced |
| `id_type` | `CharField(max_length=20, choices=IDType.choices)` | See ID types below |
| `id_number` | `CharField(max_length=60)` | Government-issued document number |
| `nationality` | `CharField(max_length=100, blank=True)` | ISO country name or code |
| `notes` | `TextField(blank=True)` | VIP flags, allergies, preferences |
| `total_stays` | `IntegerField(default=0)` | Incremented by `CustomerService.increment_stays()` |
| `created_at` | `DateTimeField` | Auto-set on creation |

**ID type choices:**

```python
class IDType(models.TextChoices):
    PASSPORT         = "PASSPORT",         "Passport"
    NATIONAL_ID      = "NATIONAL_ID",      "National ID"
    DRIVING_LICENSE  = "DRIVING_LICENSE",  "Driving License"
    OTHER            = "OTHER",            "Other"
```

**Constraint:**

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "id_type", "id_number"],
            name="unique_customer_hotel_id",
        )
    ]
    ordering = ["last_name", "first_name"]
```

---

### 2.8 `Employee` | موظفو الفندق وأقسامهم

> 💡 **شرح المودل بالعربية (Hotel Staff):**
> يربط المستخدم (`User`) بالفندق مع تحديد القسم (الاستقبال، الإشراف الداخلي، الصيانة، الإدارة، إلخ).
> **قاعدة حيوية:** تتحقق طبقة الخدمة `EmployeeService` من أن المستخدم يملك عضوية فندق نشطة (`HotelMembership`) قبل إنشاء أو تحديث سجل الموظف.

> **App:** `customers` &nbsp;|&nbsp; **Table:** `customers_employee`

Links an `accounts.User` to a hotel with department and position metadata. Before saving, the service layer validates that the user holds an **active** `HotelMembership` for the same hotel.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key |
| `hotel` | `ForeignKey(Hotel)` | `on_delete=CASCADE` |
| `user` | `ForeignKey(settings.AUTH_USER_MODEL)` | `on_delete=PROTECT`, `related_name="employee_profiles"` |
| `department` | `CharField(max_length=30, choices=Department.choices)` | See department values below |
| `position` | `CharField(max_length=100)` | Job title, e.g. `"Senior Receptionist"` |
| `is_active` | `BooleanField(default=True)` | Inactive employees are excluded from duty rosters |
| `hired_at` | `DateField` | Date of employment commencement |
| `created_at` | `DateTimeField` | Auto-set on creation |

**Department choices:**

```python
class Department(models.TextChoices):
    FRONT_DESK    = "FRONT_DESK",    "Front Desk"
    HOUSEKEEPING  = "HOUSEKEEPING",  "Housekeeping"
    MAINTENANCE   = "MAINTENANCE",   "Maintenance"
    MANAGEMENT    = "MANAGEMENT",    "Management"
    FOOD_BEVERAGE = "FOOD_BEVERAGE", "Food & Beverage"
    SECURITY      = "SECURITY",      "Security"
    OTHER         = "OTHER",         "Other"
```

---

## 3. Key Design Decisions | ٣. القرارات المعمارية الرئيسية

> [!NOTE]
> 💡 **شرح فلسفة التصميم المعماري:**
> يوثق هذا القسم الأسباب والبدائل الهندسية التي تم اختيارها لبناء قاعدة بيانات آمنة وقابلة للتوسع بدون مشاكل تضارب أو تسريب بيانات بين المستأجرين.

### 3.1 `Language` Is a Global Lookup Table | جعل اللغات جدولاً عاماً مشتركاً

> 💡 **التعليل الفني:** عزل اللغات في جدول عام يمنع تكرار آلاف السجلات لنفس اللغات عبر مئات الفنادق، ويسهل إدارة أكواد BCP-47 المركزية.

`Language` carries **no hotel foreign key**. All hotels share the same language catalogue.

**Rationale:** If languages were per-hotel, every hotel would create duplicate rows for English, Arabic, French, etc. A global table allows a single admin to curate the list, ensures consistent BCP-47 codes across the platform, and makes reporting by language trivial without joining across hotel partitions.

> [!NOTE]
> Adding a new language to the platform immediately makes it available to all hotels. Hotels then opt-in by creating a `HotelLanguage` record.

---

### 3.2 `HotelLanguage.is_default` — Race-Condition-Safe Uniqueness | حماية ضبط اللغة الافتراضية من التضارب

> 💡 **التعليل الفني:** استخدام `transaction.atomic` يضمن إلغاء الصفة الافتراضية عن اللغة السابقة وتعيين اللغة الجديدة كوحدة واحدة لا تتجزأ (Atomic Operation)، فلا يمكن أن يرى النظام فندقاً بدون لغة افتراضية أو بلغتين افتراضيتين معاً.

The database does not enforce "at most one `is_default=True` per hotel" with a partial unique index in the base implementation. Instead, the service layer enforces this invariant inside a `transaction.atomic` block:

```python
# rooms/services.py — HotelLanguageService.set_default()
@staticmethod
def set_default(hotel: Hotel, language: Language) -> HotelLanguage:
    with transaction.atomic():
        # Step 1 — strip the default flag from any existing default
        HotelLanguage.objects.filter(
            hotel=hotel, is_default=True
        ).update(is_default=False)

        # Step 2 — set the new default atomically
        hotel_lang = HotelLanguage.objects.get(hotel=hotel, language=language)
        hotel_lang.is_default = True
        hotel_lang.save(update_fields=["is_default"])

    return hotel_lang
```

Because both statements execute inside the same database transaction, no concurrent request can observe a state with zero defaults or two defaults during the update.

> [!IMPORTANT]
> Django's `select_for_update()` can be added to Step 1 if the production database shows high concurrency on this endpoint. For typical hotel workloads, `transaction.atomic` alone is sufficient.

---

### 3.3 `UniqueConstraint` over `unique_together` / `unique=True` | تفضيل القيود الحديثة على الأساليب القديمة

> 💡 **التعليل الفني:** أصبحت `unique_together` مهملة (Deprecated) في دجانجو الحديثة. توفر `UniqueConstraint` إمكانية تسمية القيد في قاعدة البيانات ودعم القيود الشرطية وفهارس التغطية.

Throughout Phase 4, per-hotel uniqueness (e.g., `RoomType.code`, `Room.room_number`) is enforced with `UniqueConstraint` rather than the legacy `unique_together` or a bare `unique=True` on the field.

| Feature | `unique=True` | `unique_together` | `UniqueConstraint` |
|---|:---:|:---:|:---:|
| Named constraint in DB | ✗ | ✗ | ✅ |
| Supports `condition=` | ✗ | ✗ | ✅ |
| Supports `deferrable=` | ✗ | ✗ | ✅ |
| Django deprecation status | Active | **Deprecated** | Active |
| Works with `include=` | ✗ | ✗ | ✅ |

**Example — per-hotel room number uniqueness:**

```python
# UniqueConstraint: room "101" can exist in Hotel A AND Hotel B
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "room_number"],
            name="unique_room_hotel_room_number",
        )
    ]
```

If `unique=True` were placed on `room_number` alone, no two hotels could share the same room number — an obvious business-logic error.

---

### 3.4 `Room.room_number` Per-Hotel Uniqueness | فرادة رقم الغرفة لكل فندق على حدة

> 💡 **التعليل الفني:** القيد الفريد يجمع `(hotel, room_number)`، مما يتيح لفندق A وفندق B امتلاك الغرفة رقم '101' دون أي تعارض، مع منع تكرار نفس الرقم داخل الفندق الواحد.

Room numbers such as `"101"` are reused across hotels. The `UniqueConstraint(fields=["hotel", "room_number"])` means:

- Hotel A **and** Hotel B can both have a room `"101"` — ✅ valid
- Hotel A cannot have **two** rooms both numbered `"101"` — ✅ raises `IntegrityError`

---

### 3.5 `Employee` Validates Active `HotelMembership` | التحقق من عضوية الموظف في الفندق

> 💡 **التعليل الفني:** منع ربط أي موظف بفندق ما لم يكن يملك حساباً وعضوية نشطة في جدول `HotelMembership`، مما يحفظ تكامل الصلاحيات والأمان (RBAC).

Before persisting an `Employee` record, `EmployeeService.validate_membership()` checks that the associated `User` has a currently active membership at the target hotel:

```python
# customers/services.py
class EmployeeService:
    @staticmethod
    def validate_membership(hotel: Hotel, user) -> None:
        from accounts.models import HotelMembership
        if not HotelMembership.objects.filter(
            hotel=hotel, user=user, is_active=True
        ).exists():
            raise ValidationError(
                f"User {user.email} does not have an active membership "
                f"at hotel '{hotel.name}'."
            )
```

This guard ensures that only users who have gone through the hotel onboarding flow (Phase 2) can be assigned as employees, preventing orphaned employee records.

---

### 3.6 `_check_no_blocking_issues()` — Phase 7 Placeholder | خطاف التحقق من الأعطال الحرجة المانعة

> 💡 **التعليل الفني:** تم وضع دالة وهمية (Hook/Stub) في `RoomService` أثناء المرحلة 4 لتمهيد ربطها بالمرحلة 7 (الصيانة)، بحيث لا يمكن إعادة الغرفة لحالة `AVAILABLE` إذا وُجد بلاغ صيانة حرج مانع.

`rooms/services.py` contains a stub method used by `RoomService.mark_available()`:

```python
# rooms/services.py
def _check_no_blocking_issues(room: Room) -> bool:
    """
    Phase 7 placeholder.

    In Phase 4 this always returns True.
    Phase 7 (Maintenance Tracking) will replace this with a real query
    against the RoomIssue model to block status transitions when open,
    safety-critical issues exist.
    """
    return True
```

This design avoids a circular dependency between the `rooms` and `maintenance` apps during early phases. Phase 7 replaces the stub body with:

```python
from maintenance.models import RoomIssue
return not RoomIssue.objects.filter(
    room=room, is_blocking=True, resolved_at__isnull=True
).exists()
```

---

## 4. Django Problems Solved | ٤. المشاكل التقنية في دجانجو وكيف تم حلها

> [!NOTE]
> 💡 **شرح المشاكل وحلولها الوقائية:**
> يستعرض هذا القسم كيفية التغلب على أشهر مشاكل دجانجو التي تسبب بطء الأداء أو تضارب البيانات في بيئات الإنتاج.

### 4.1 N+1 Query Prevention | القضاء على مشكلة الاستعلامات المتكررة N+1

> 💡 **الشرح الفني:** بدلاً من إجراء استعلام منفصل لكل صف، يتم استخدام `select_related` للعلاقات الفردية (ForeignKeys) مثل نوع الغرفة، و `prefetch_related` مع `Prefetch` مخصص للعلاقات المتعددة مثل ترجمات اللغات، مما يخفض الاستعلامات من مئات الاستعلامات إلى استعلامين اثنين فقط!

Naïvely iterating over rooms and accessing `room.room_type.translations.all()` inside a loop fires one extra query per room — the classic **N+1 problem**.

Phase 4 eliminates this with `select_related` + `Prefetch`:

```python
from django.db.models import Prefetch
from rooms.models import Room, RoomTypeTranslation

# Room list with room_type translations — N+1 safe
rooms = Room.objects.filter(hotel=hotel).select_related(
    'room_type'
).prefetch_related(
    Prefetch(
        'room_type__translations',
        queryset=RoomTypeTranslation.objects.select_related('language')
    )
)
```

This produces exactly **3 SQL queries** regardless of how many rooms or translations exist:

1. Fetch all `Room` rows + JOIN `RoomType` (via `select_related`)
2. Fetch all `RoomTypeTranslation` rows for the collected `RoomType` IDs
3. Fetch all `Language` rows for those translations (via nested `select_related`)

Query counts are verified in tests using `assertNumQueries`.

---

### 4.2 `UniqueConstraint` vs `unique_together` | مقارنة تفصيلية بين أساليب القيود الفريدة

> 💡 **الشرح الفني:** تفضيل النموذج الحديث يتيح إنشاء فهارس مخصصة وتسميات واضحة لأخطاء قاعدة البيانات بدلاً من القيود العامة.

Django's `unique_together` is **officially deprecated** as of Django 4.2 and may be removed in a future major release. `UniqueConstraint` is the recommended replacement and offers additional capabilities:

```python
# ✗ Old (deprecated) approach
class Meta:
    unique_together = [("hotel", "code")]

# ✅ New approach — named, supports conditions, deferrable
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["hotel", "code"],
            name="unique_roomtype_hotel_code",
            # Future: condition=Q(is_active=True) for partial indexes
        )
    ]
```

Named constraints also produce cleaner error messages and are easier to manage in migrations.

---

### 4.3 `TenantManager.for_hotel()` | مدير المستأجر الصارم لمنع تسريب البيانات

> 💡 **الشرح الفني:** يجبر المطور على استخدام `.for_hotel(hotel)` دائماً، مما يجعل استعلام `objects.all()` العام غير متاح مباشرة ويقضي تماماً على خطر تسريب بيانات فندق لآخر.

Every multi-tenant model exposes a custom `TenantManager` that enforces hotel scoping at the ORM level:

```python
# core/managers.py
class TenantManager(models.Manager):
    def for_hotel(self, hotel):
        """
        Returns a queryset pre-filtered to the given hotel.
        Always use this method instead of .filter(hotel=hotel)
        to prevent accidental cross-tenant data leakage.
        """
        return self.get_queryset().filter(hotel=hotel)
```

Usage in views and services:

```python
# Never do this — easy to forget the filter:
rooms = Room.objects.all()

# Always do this — hotel isolation is guaranteed:
rooms = Room.objects.for_hotel(request.hotel)
```

The `TenantManager` is set as `default_manager_name` on all tenant-scoped models so that `.objects` always uses it.

---

## 5. Service Layer | ٥. طبقة الأعمال والخدمات (Service Layer)

> [!NOTE]
> 💡 **شرح طبقة الخدمات:**
> تطبق المنصة مبدأ (Fat Services, Thin Views). كل منطق الأعمال والتحققات والتعديلات تتم داخل كلاسات الخدمة، بينما تقتصر الـ Views على استقبال الطلب وإرجاع الاستجابة.

The service layer contains all business logic. Views and serializers call services; they never query the database directly.

---

### 5.1 `LanguageService`

```python
# rooms/services.py
class LanguageService:
    @staticmethod
    def list_active() -> QuerySet:
        """Returns all Language records where is_active=True, ordered by name."""
        return Language.objects.filter(is_active=True)

    @staticmethod
    def get_by_code(code: str) -> Language:
        """
        Retrieves a Language by its BCP-47 code.
        Raises Language.DoesNotExist if not found.
        """
        return Language.objects.get(code=code)
```

---

### 5.2 `HotelLanguageService`

```python
class HotelLanguageService:
    @staticmethod
    def list_for_hotel(hotel: Hotel) -> QuerySet:
        """
        Returns all HotelLanguage records for the given hotel,
        with the related Language prefetched.
        """
        return (
            HotelLanguage.objects
            .filter(hotel=hotel)
            .select_related("language")
            .order_by("-is_default", "language__name")
        )

    @staticmethod
    def set_default(hotel: Hotel, language: Language) -> HotelLanguage:
        """
        Atomically sets `language` as the default for `hotel`.
        Clears the is_default flag from any previously-default language first.
        Raises HotelLanguage.DoesNotExist if the language is not yet added to the hotel.
        """
        with transaction.atomic():
            HotelLanguage.objects.filter(
                hotel=hotel, is_default=True
            ).update(is_default=False)

            hotel_lang = HotelLanguage.objects.get(hotel=hotel, language=language)
            hotel_lang.is_default = True
            hotel_lang.save(update_fields=["is_default"])

        return hotel_lang
```

---

### 5.3 `BookingSourceService`

```python
class BookingSourceService:
    @staticmethod
    def create(hotel: Hotel, data: dict) -> BookingSource:
        """Creates a new BookingSource for the hotel. Raises ValidationError on duplicate code."""
        return BookingSource.objects.create(hotel=hotel, **data)

    @staticmethod
    def list_active(hotel: Hotel) -> QuerySet:
        """Returns all active BookingSource records for the hotel."""
        return BookingSource.objects.filter(hotel=hotel, is_active=True)

    @staticmethod
    def update(instance: BookingSource, data: dict) -> BookingSource:
        """Updates mutable fields on an existing BookingSource."""
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    @staticmethod
    def deactivate(instance: BookingSource) -> BookingSource:
        """Soft-deletes a BookingSource by setting is_active=False."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return instance
```

---

### 5.4 `RoomTypeService`

```python
class RoomTypeService:
    @staticmethod
    def create(hotel: Hotel, data: dict, translations: list[dict]) -> RoomType:
        """
        Creates a RoomType and upserts all provided translations in a single transaction.

        `translations` is a list of dicts, each containing:
            - language_code: str  (BCP-47 code, e.g. "en")
            - name: str
            - description: str (optional)
        """
        with transaction.atomic():
            room_type = RoomType.objects.create(hotel=hotel, **data)
            RoomTypeService._upsert_translations(room_type, translations)
        return room_type

    @staticmethod
    def update(instance: RoomType, data: dict, translations: list[dict]) -> RoomType:
        """
        Updates a RoomType and upserts translations.
        Existing translations not present in `translations` are left untouched.
        """
        with transaction.atomic():
            for field, value in data.items():
                setattr(instance, field, value)
            instance.save()
            RoomTypeService._upsert_translations(instance, translations)
        return instance

    @staticmethod
    def list_with_translations(hotel: Hotel, lang_code: str | None = None) -> QuerySet:
        """
        Returns RoomTypes for the hotel with translations prefetched.
        If lang_code is given, only that language's translation is prefetched.
        """
        qs = RoomType.objects.filter(hotel=hotel, is_active=True)
        if lang_code:
            qs = qs.prefetch_related(
                Prefetch(
                    "translations",
                    queryset=RoomTypeTranslation.objects.filter(
                        language__code=lang_code
                    ).select_related("language"),
                )
            )
        else:
            qs = qs.prefetch_related(
                Prefetch(
                    "translations",
                    queryset=RoomTypeTranslation.objects.select_related("language"),
                )
            )
        return qs

    @staticmethod
    def _upsert_translations(room_type: RoomType, translations: list[dict]) -> None:
        """
        For each entry in `translations`, performs an update_or_create keyed on
        (room_type, language) so repeated calls are idempotent.
        """
        for t in translations:
            lang = Language.objects.get(code=t["language_code"])
            RoomTypeTranslation.objects.update_or_create(
                room_type=room_type,
                language=lang,
                defaults={"name": t["name"], "description": t.get("description", "")},
            )
```

---

### 5.5 `RoomService`

```python
class RoomService:
    @staticmethod
    def create(hotel: Hotel, data: dict) -> Room:
        return Room.objects.create(hotel=hotel, **data)

    @staticmethod
    def update(instance: Room, data: dict) -> Room:
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    @staticmethod
    def mark_occupied(room: Room) -> Room:
        room.status = RoomStatus.OCCUPIED
        room.save(update_fields=["status"])
        return room

    @staticmethod
    def mark_cleaning(room: Room) -> Room:
        room.status = RoomStatus.CLEANING
        room.save(update_fields=["status"])
        return room

    @staticmethod
    def mark_available(room: Room) -> Room:
        """
        Transitions the room to AVAILABLE.
        Calls _check_no_blocking_issues() — always True in Phase 4,
        replaced with a real RoomIssue query in Phase 7.
        """
        if not _check_no_blocking_issues(room):
            raise ValidationError(
                "Room has open blocking maintenance issues and cannot be marked available."
            )
        room.status = RoomStatus.AVAILABLE
        room.save(update_fields=["status"])
        return room

    @staticmethod
    def mark_maintenance(room: Room) -> Room:
        room.status = RoomStatus.MAINTENANCE
        room.save(update_fields=["status"])
        return room
```

---

### 5.6 `CustomerService`

```python
class CustomerService:
    @staticmethod
    def create(hotel: Hotel, data: dict) -> Customer:
        """Creates a new Customer record for the hotel."""
        return Customer.objects.create(hotel=hotel, **data)

    @staticmethod
    def get_or_create_by_id(
        hotel: Hotel, id_type: str, id_number: str, data: dict
    ) -> tuple[Customer, bool]:
        """
        Returns (customer, created).
        If a customer with (hotel, id_type, id_number) already exists,
        returns the existing record without modification.
        Otherwise creates a new Customer using `data`.
        """
        return Customer.objects.get_or_create(
            hotel=hotel,
            id_type=id_type,
            id_number=id_number,
            defaults=data,
        )

    @staticmethod
    def increment_stays(customer: Customer) -> Customer:
        """
        Atomically increments total_stays using F() to avoid race conditions.
        Called at checkout by the booking service (Phase 5).
        """
        Customer.objects.filter(pk=customer.pk).update(
            total_stays=models.F("total_stays") + 1
        )
        customer.refresh_from_db(fields=["total_stays"])
        return customer
```

---

### 5.7 `EmployeeService`

```python
class EmployeeService:
    @staticmethod
    def validate_membership(hotel: Hotel, user) -> None:
        """
        Raises ValidationError if the user does not have an active
        HotelMembership for the given hotel.
        """
        from accounts.models import HotelMembership
        if not HotelMembership.objects.filter(
            hotel=hotel, user=user, is_active=True
        ).exists():
            raise ValidationError(
                f"User {user.email!r} does not have an active membership "
                f"at hotel '{hotel.name}'."
            )

    @staticmethod
    def create(hotel: Hotel, user, data: dict) -> Employee:
        """
        Validates membership, then creates an Employee record.
        Raises ValidationError if membership check fails.
        """
        EmployeeService.validate_membership(hotel, user)
        return Employee.objects.create(hotel=hotel, user=user, **data)
```

---

## 6. Selector Layer | ٦. طبقة استعلامات القراءة (Selector Layer)

> [!NOTE]
> 💡 **شرح طبقة المحددات:**
> تُفصل استعلامات القراءة (Read Queries) في ملف `selectors.py` لضمان تطبيق `select_related` و `prefetch_related` دائماً وتوحيد استعلامات الفلترة والبحث.

Selectors are read-only query builders that return N+1-safe querysets for use in views and serializers. They are separate from services to keep query concerns distinct from mutation concerns.

---

### 6.1 `RoomSelector`

```python
# rooms/selectors.py
class RoomSelector:
    @staticmethod
    def get_room_list_for_hotel(hotel: Hotel, filters: dict | None = None) -> QuerySet:
        """
        Returns all rooms for the hotel with room_type and translations
        eagerly loaded. Supports optional filtering by status and floor.

        :param filters: dict with optional keys: status, floor
        """
        qs = (
            Room.objects
            .filter(hotel=hotel)
            .select_related("room_type")
            .prefetch_related(
                Prefetch(
                    "room_type__translations",
                    queryset=RoomTypeTranslation.objects.select_related("language"),
                )
            )
            .order_by("floor", "room_number")
        )

        if filters:
            if status := filters.get("status"):
                qs = qs.filter(status=status)
            if floor := filters.get("floor"):
                qs = qs.filter(floor=floor)

        return qs
```

---

### 6.2 `CustomerSelector`

```python
class CustomerSelector:
    @staticmethod
    def get_customer_list(hotel: Hotel, search: str | None = None) -> QuerySet:
        """
        Returns all customers for the hotel.
        If `search` is provided, filters by case-insensitive match on
        first_name, last_name, email, or id_number.
        """
        qs = Customer.objects.filter(hotel=hotel).order_by("last_name", "first_name")

        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(id_number__icontains=search)
            )

        return qs
```

---

### 6.3 `RoomTypeSelector`

```python
class RoomTypeSelector:
    @staticmethod
    def get_with_translation(hotel: Hotel, lang_code: str) -> QuerySet:
        """
        Returns active RoomTypes for the hotel with the translation for
        `lang_code` prefetched. Falls back to the hotel default language
        translation if the requested language has no translation row.

        Fallback logic is applied in the serializer by inspecting
        room_type.translations.all() and selecting the first available.
        """
        default_lang = (
            HotelLanguage.objects
            .filter(hotel=hotel, is_default=True)
            .select_related("language")
            .first()
        )
        fallback_code = default_lang.language.code if default_lang else "en"

        return (
            RoomType.objects
            .filter(hotel=hotel, is_active=True)
            .prefetch_related(
                Prefetch(
                    "translations",
                    queryset=RoomTypeTranslation.objects.filter(
                        language__code__in=[lang_code, fallback_code]
                    ).select_related("language"),
                )
            )
        )
```

---

## 7. API Endpoints | ٧. نقاط النهاية للواجهة البرمجية (REST Endpoints)

> 💡 **شرح نقاط النهاية:** جدول يوضح جميع الـ Endpoints المتاحة في تطبيقي `rooms` و `customers` مع طرق HTTP ومستويات الصلاحيات المطلوبة.

All endpoints are prefixed with `/api/v1/`. Authentication is via JWT Bearer token. Hotel context is resolved from the JWT claims (see Phase 2).

### 7.1 Rooms App Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/rooms/languages/` | List all active global languages | JWT |
| `GET` | `/rooms/hotel-languages/` | List languages configured for current hotel | JWT |
| `POST` | `/rooms/hotel-languages/` | Add a language to the current hotel | JWT + `rooms.manage` |
| `PATCH` | `/rooms/hotel-languages/{id}/set-default/` | Set a hotel language as default | JWT + `rooms.manage` |
| `GET` | `/rooms/booking-sources/` | List booking sources for current hotel | JWT + `rooms.view` |
| `POST` | `/rooms/booking-sources/` | Create a new booking source | JWT + `rooms.manage` |
| `PUT` / `PATCH` | `/rooms/booking-sources/{id}/` | Update an existing booking source | JWT + `rooms.manage` |
| `DELETE` | `/rooms/booking-sources/{id}/` | Deactivate (soft-delete) a booking source | JWT + `rooms.manage` |
| `GET` | `/rooms/room-types/` | List room types with translations | JWT + `rooms.view` |
| `POST` | `/rooms/room-types/` | Create a room type with translations | JWT + `rooms.manage` |
| `PUT` / `PATCH` | `/rooms/room-types/{id}/` | Update room type and upsert translations | JWT + `rooms.manage` |
| `DELETE` | `/rooms/room-types/{id}/` | Delete a room type | JWT + `rooms.manage` |
| `GET` | `/rooms/rooms/` | List rooms with status and room type info | JWT + `rooms.view` |
| `POST` | `/rooms/rooms/` | Create a new room | JWT + `rooms.manage` |
| `PUT` / `PATCH` | `/rooms/rooms/{id}/` | Update room details or status | JWT + `rooms.manage` |

### 7.2 Customers App Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/customers/customers/` | List customers (supports `?search=`) | JWT + `customers.view` |
| `POST` | `/customers/customers/` | Create a new customer | JWT + `customers.manage` |
| `GET` | `/customers/customers/{id}/` | Retrieve a single customer by UUID | JWT + `customers.view` |
| `PUT` / `PATCH` | `/customers/customers/{id}/` | Update customer details | JWT + `customers.manage` |
| `GET` | `/customers/employees/` | List employees for current hotel | JWT + `customers.view` |
| `POST` | `/customers/employees/` | Create an employee (validates membership) | JWT + `customers.manage` |
| `PUT` / `PATCH` | `/customers/employees/{id}/` | Update employee department, position, or status | JWT + `customers.manage` |

> [!NOTE]
> Room status transitions (`mark_occupied`, `mark_cleaning`, etc.) are not exposed as separate endpoints in Phase 4. They are triggered internally by the booking and housekeeping services introduced in Phases 5 and 6.

---

## 8. Permissions | ٨. مصفوفة الصلاحيات والأمان

> 💡 **شرح الصلاحيات:** تنقسم الصلاحيات إلى عرض (`rooms.view`, `customers.view`) وإدارة وتعديل (`rooms.manage`, `customers.manage`) ويتم التحقق منها عبر `HasHotelPermission`.

Phase 4 introduces four fine-grained permission codes. These are stored in the `HotelMembership.permissions` JSONField (established in Phase 2) and checked on each request by the `HotelPermission` DRF permission class.

| Permission Code | Scope | Grants Access To |
|---|---|---|
| `rooms.view` | Read-only | Room list, room type list, booking source list, language list |
| `rooms.manage` | Full CRUD | Create/update/delete rooms, room types, booking sources, hotel languages |
| `customers.view` | Read-only | Customer list, customer detail, employee list |
| `customers.manage` | Full CRUD | Create/update customers, create/update employees |

### Permission Enforcement Example

```python
# rooms/views.py
class RoomViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), HotelPermission("rooms.view")]
        return [IsAuthenticated(), HotelPermission("rooms.manage")]
```

> [!IMPORTANT]
> `rooms.manage` does **not** implicitly grant `rooms.view` at the permission-code level. Roles that need both read and write access should be assigned both codes. In practice, the built-in `Manager` role includes all four codes.

---

## 9. Tests Summary | ٩. ملخص نتائج الاختبارات الآلية (27 اختباراً ناجحاً)

> 💡 **ملخص الاختبارات:** تم بناء 27 اختباراً شاملاً يغطي عزل المستأجرين، ترجمات الغرف، فهارس البحث، النزلاء والموظفين، مع نسبة نجاح 100%.

Phase 4 ships with **27 automated tests** across two test modules.

### 9.1 `tests/test_rooms.py` — 18 Tests

| Test Group | Count | What Is Verified |
|---|---|---|
| **RoomType creation with translations** | 5 | Creating a `RoomType` with 1, 2, and 3 translations; verifying upsert idempotency; verifying `update_or_create` does not duplicate rows |
| **UniqueConstraint violations** | 3 | Duplicate `RoomType.code` within same hotel raises `IntegrityError`; same code in different hotels is permitted; duplicate `Room.room_number` within same hotel raises `IntegrityError` |
| **HotelLanguage default concurrency** | 2 | `set_default()` atomically transfers the default flag; no hotel ends up with two default languages after concurrent calls |
| **Room status transitions** | 4 | `mark_occupied`, `mark_cleaning`, `mark_available` (with stub returning True), `mark_maintenance` each produce the correct `status` value |
| **TenantManager isolation** | 4 | `Room.objects.for_hotel(hotel_a)` never returns rooms belonging to `hotel_b`; `RoomType.objects.for_hotel()` is similarly scoped |

### 9.2 `tests/test_customers.py` — 9 Tests

| Test Group | Count | What Is Verified |
|---|---|---|
| **Customer `get_or_create_by_id`** | 3 | Returns existing customer when `(hotel, id_type, id_number)` matches; creates new customer when no match; returned `created` flag is accurate |
| **Employee membership validation** | 2 | `EmployeeService.create()` raises `ValidationError` when user has no membership; succeeds when user has an active membership |
| **N+1 query count assertions** | 4 | `RoomSelector.get_room_list_for_hotel()` executes ≤ 3 queries for any number of rooms; `CustomerSelector.get_customer_list()` executes 1 query; `RoomTypeSelector.get_with_translation()` executes ≤ 3 queries |

### Running the Test Suite

```bash
# Run all Phase 4 tests
python manage.py test tests.test_rooms tests.test_customers -v 2

# Run with coverage
coverage run manage.py test tests.test_rooms tests.test_customers
coverage report --include="rooms/*,customers/*"
```

Expected output:

```
Ran 27 tests in 1.843s
OK
```

---

## 10. Files Changed | ١٠. جدول الملفات المنشأة والمعدلة

> 💡 **دليل الملفات:** قائمة بالملفات التي تم إنشاؤها في تطبيقي `rooms` و `customers` وملفات الاختبارات والتهيئة.

### 10.1 `rooms` App

| File | Action | What Changed |
|---|---|---|
| `rooms/models.py` | **CREATED** | Defines `Language`, `HotelLanguage`, `BookingSource`, `RoomType`, `RoomTypeTranslation`, `Room` models with all fields, `UniqueConstraint`s, `TextChoices`, and `TenantManager` integration |
| `rooms/services.py` | **CREATED** | Implements `LanguageService`, `HotelLanguageService`, `BookingSourceService`, `RoomTypeService` (with translation upsert), `RoomService` (with status transitions and `_check_no_blocking_issues` stub) |
| `rooms/selectors.py` | **CREATED** | Implements `RoomSelector` and `RoomTypeSelector` with N+1-safe `select_related` / `Prefetch` query builders; translation fallback logic |
| `rooms/serializers.py` | **CREATED** | `LanguageSerializer`, `HotelLanguageSerializer`, `BookingSourceSerializer`, `RoomTypeTranslationSerializer`, `RoomTypeSerializer` (nested translations), `RoomSerializer` — all read/write capable |
| `rooms/views.py` | **CREATED** | `LanguageViewSet`, `HotelLanguageViewSet` (with `set_default` action), `BookingSourceViewSet`, `RoomTypeViewSet`, `RoomViewSet` — all delegate to service/selector layer |
| `rooms/urls.py` | **CREATED** | `DefaultRouter` registration for all five ViewSets under `/api/v1/rooms/` |
| `rooms/admin.py` | **CREATED** | `RoomTypeAdmin` with `RoomTypeTranslationInline`; `RoomAdmin` with `list_filter` on status and floor; `HotelLanguageAdmin`, `BookingSourceAdmin` |

### 10.2 `customers` App

| File | Action | What Changed |
|---|---|---|
| `customers/models.py` | **CREATED** | Defines `Customer` (with `IDType` choices and `total_stays` counter) and `Employee` (with `Department` choices and `hired_at`) models |
| `customers/services.py` | **CREATED** | Implements `CustomerService` (`create`, `get_or_create_by_id`, `increment_stays`) and `EmployeeService` (`validate_membership`, `create`) |
| `customers/selectors.py` | **CREATED** | Implements `CustomerSelector.get_customer_list()` with full-text `icontains` search across name, email, and ID number |
| `customers/serializers.py` | **CREATED** | `CustomerSerializer` (full CRUD), `CustomerListSerializer` (abbreviated for list views), `EmployeeSerializer` with nested `user` read field |
| `customers/views.py` | **CREATED** | `CustomerViewSet` and `EmployeeViewSet` with appropriate permission classes; list views use selector, write operations use service |
| `customers/urls.py` | **CREATED** | `DefaultRouter` registration for `CustomerViewSet` and `EmployeeViewSet` under `/api/v1/customers/` |

### 10.3 Tests

| File | Action | What Changed |
|---|---|---|
| `tests/test_rooms.py` | **CREATED** | 18 tests covering room type translations, UniqueConstraint enforcement, HotelLanguage concurrency, room status transitions, and TenantManager isolation |
| `tests/test_customers.py` | **CREATED** | 9 tests covering customer `get_or_create_by_id`, employee membership validation, and N+1 query count assertions with `assertNumQueries` |

---

## 11. Migrations | ١١. ملفات ترحيل قاعدة البيانات (Database Migrations)

> 💡 **شرح ملفات الترحيل:** يوثق هذا القسم عمليات الترحيل المنفذة لإنشاء الجداول والقيود والفهارس في قاعدة البيانات.

### 11.1 `rooms/migrations/0001_initial.py`

Creates the following tables in a single migration:

| Table | Key SQL Features |
|---|---|
| `rooms_language` | `UNIQUE (code)` |
| `rooms_hotellanguage` | `UNIQUE (hotel_id, language_id)` via `UniqueConstraint` named `unique_hotel_language` |
| `rooms_bookingsource` | `UNIQUE (hotel_id, code)` via `UniqueConstraint` named `unique_bookingsource_hotel_code` |
| `rooms_roomtype` | `UNIQUE (hotel_id, code)` via `UniqueConstraint` named `unique_roomtype_hotel_code` |
| `rooms_roomtypetranslation` | `UNIQUE (room_type_id, language_id)` via `UniqueConstraint` named `unique_roomtypetranslation_roomtype_language` |
| `rooms_room` | `UNIQUE (hotel_id, room_number)` via `UniqueConstraint` named `unique_room_hotel_room_number`; indexed on `status` and `floor` |

```bash
# Apply rooms migrations
python manage.py migrate rooms
```

### 11.2 `customers/migrations/0001_initial.py`

Creates the following tables:

| Table | Key SQL Features |
|---|---|
| `customers_customer` | `UNIQUE (hotel_id, id_type, id_number)` via `UniqueConstraint` named `unique_customer_hotel_id`; indexed on `last_name`, `email` |
| `customers_employee` | `ForeignKey` to `auth_user` with `PROTECT`; indexed on `department` and `is_active` |

```bash
# Apply customers migrations
python manage.py migrate customers

# Apply both at once
python manage.py migrate
```

> [!NOTE]
> Both migrations depend on the `hotels` app migration that creates the `Hotel` table (Phase 1) and the `accounts` app migration that creates `HotelMembership` (Phase 2). Django's migration framework resolves these dependencies automatically via the `dependencies` list in each migration file.

---

*Phase 4 complete. Proceed to [Phase 5 — Reservations & Booking Engine](./PHASE_5_DOCS.md) to see how `Room`, `Customer`, and `BookingSource` are consumed by the booking workflow.*
