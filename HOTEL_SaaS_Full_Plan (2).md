# 🏨 HOTEL SaaS — خطة البناء الكاملة (Django + React)

> اسم المشروع: **HOTEL SaaS**
> اسم مشروع Django: **project**
> نوع النظام: **Multi-Tenant Hotel Management SaaS Platform**

هذا المستند هو الدمج النهائي بين الملفين اللي بعتهملي، مرتب في **12 Phase** تنفيذية، وكل Phase فيها:
- الهدف المعماري
- الـModels / Django Apps
- مشاكل Django المتوقعة في الـPhase دي تحديدًا (N+1, Query Optimization, Indexing, Celery, Caching, Serializers, Nested Serializers, Validation...) وإزاي نتعامل معاها
- جزء React المقابل
- الـPrompt الجاهز للتنفيذ

---

## 🧱 Phase 0 — تجهيز المشروع (قبل أي Phase)

### الأوامر
```bash
django-admin startproject project .
cd project
python manage.py startapp accounts
```

### هيكلة المجلدات المتفق عليها
```
project/
├── config/            (settings, urls, celery.py, asgi/wsgi)
├── apps/
│   ├── accounts/ tenants/ features/ subscriptions/
│   ├── rooms/ customers/ reservations/ payments/
│   ├── finance/ housekeeping/ maintenance/ complaints/ employees/
│   ├── documents/ notifications/
│   ├── reports/ analytics/
│   ├── websites/ languages/
│   └── audit/
├── common/
│   ├── models/ permissions/ middleware/ exceptions/
│   ├── pagination/ validators/ utils/
└── manage.py

frontend/
├── src/
│   ├── app/ core/{api,auth,permissions,features,i18n,layouts}/
│   ├── modules/{dashboard,rooms,customers,reservations,finance,...}/
│   └── shared/
```

### Django settings مهمة من أول يوم
- `settings/base.py` + `development.py` + `production.py` (فصل environments)
- `django-environ` لقراءة `.env`
- `REST_FRAMEWORK` config: pagination class موحدة، exception handler موحد، versioning
- تفعيل **django-silk** أو **django-debug-toolbar** في التطوير فقط، عشان نكتشف N+1 من أول Phase
- `CONN_MAX_AGE` في `DATABASES` لتقليل overhead الاتصال بالـPostgreSQL
- تجهيز `celery.py` و Redis broker من البداية حتى لو مش هنستخدمهم إلا في Phase 6/8

### Prompt
```
Bootstrap a Django + DRF + PostgreSQL project named "project"
(created via `django-admin startproject project .`) plus a React (Vite) frontend
named "HOTEL SaaS".

Set up:
- config/settings split into base/development/production
- environment variables via django-environ
- DRF global config: pagination, versioning, centralized exception handler
- celery.py wired to Redis (broker not used yet, just wired)
- django-debug-toolbar / django-silk in development only
- CONN_MAX_AGE and connection pooling readiness
- pre-commit, black, isort, flake8
- pytest + pytest-django + factory_boy
- React app structure: app/ core/ modules/ shared/
- React Router, Axios/fetch API client, i18n foundation, RTL/LTR toggle

Do not implement any hotel business domain yet.
Report: files created, packages installed, and how to run both servers.
```

---

## 🟦 Phase 1 — Foundation

**الهدف:** بنية تحتية نظيفة قبل أي Business Logic.

### Django
- Apps فاضية بس مسجلة: كل الدومينز المذكورة فوق
- `common/models/`: هنجهزها فاضية دلوقتي، هنملاها في Phase 2
- Error handling موحد (custom `exception_handler` في DRF يرجع شكل JSON ثابت لكل الأخطاء)
- Logging: `LOGGING` dict بتسجيل structured logs (JSON) عشان production
- OpenAPI عن طريق `drf-spectacular`

### مشاكل Django المتوقعة هنا
| المشكلة | الحل |
|---|---|
| صعوبة تتبع الأخطاء لاحقًا | Structured logging + request_id middleware من الآن |
| Pagination مختلفة بين الـviews | `PageNumberPagination` مخصصة في `common/pagination` تتفرض على كل الـViewSets |
| توسع الـsettings.py | تقسيمها من أول يوم (base/dev/prod) |

### React
- Router + Layout عام (Sidebar/Topbar placeholders)
- API client (axios instance + interceptors لـ401/403)
- i18n foundation (react-i18next) + RTL/LTR switch
- Error boundary + Loading/Empty states كـshared components

### Prompt
```
Implement Phase 1 only.

Django: environment-based settings, API versioning, centralized DRF exception
handling returning a consistent JSON error shape, custom pagination class,
filtering (django-filter), OpenAPI via drf-spectacular, structured logging
with a request-id middleware, and pytest test scaffolding.

React: routing, a global layout, an API client with 401/403 interceptors,
i18n foundation, RTL/LTR support, and shared LoadingState/ErrorState/EmptyState
components.

Do not implement hotel business domains yet.
Report files created, dependencies, and how errors/pagination look in the API.
```

---

## 🟩 Phase 2 — Multi-Tenancy + Core Abstract Models

**الهدف:** Hotel هو جذر الـTenant، وكل حاجة تانية تتبعه.

### Django Models
```python
# common/models/base.py
class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta: abstract = True

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class ActiveModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    class Meta: abstract = True

class HotelOwnedMixin(models.Model):
    hotel = models.ForeignKey("tenants.Hotel", on_delete=models.CASCADE,
                               related_name="%(class)ss", db_index=True)
    class Meta: abstract = True

class BaseModel(UUIDModel, TimeStampedModel, ActiveModel):
    class Meta: abstract = True
```

```python
# apps/tenants/models.py
class Hotel(BaseModel):
    name, slug, email, phone, address, timezone,
    default_currency, default_language, status, subdomain

class HotelSettings(BaseModel):
    hotel = OneToOneField(Hotel)
    exchange_rate_mode, checkin_time, checkout_time, ...
```

### مشاكل Django المتوقعة
- **Indexing:** كل FK لـ`hotel` لازم `db_index=True` (موجودة تلقائيًا لكن أكدها) + composite index على (`hotel_id`, `created_at`) للجداول اللي هتتفلتر بالتاريخ كتير (سيبقى مهم من Phase 5 وما بعد).
- **Tenant leakage خطر جدًا:** لازم نعمل **Manager مخصص** (`TenantManager`) بيرفض أي `.objects.all()` بدون `hotel` فلتر صريح في القراءة داخل Views، ونستخدم Middleware/Context لحقن `request.hotel`.
- **N+1 من البداية:** أي Selector يرجع Queryset لازم يتصمم وهو محسّن (`select_related("hotel")`) بدل ما نصلحه بعدين.
- **Migrations:** لازم نضيف DB-level `CheckConstraint`/`UniqueConstraint` scoped بالـ`hotel` (مثلاً `unique_together = ("hotel", "room_number")` هنستخدمها في Phase 4).

### React
- `core/features` لسه هيستنى، بس هنجهز `HotelContext` (active hotel) فاضي.

### Prompt
```
Implement Phase 2 only.

Create in common/models: UUIDModel, TimeStampedModel, ActiveModel,
HotelOwnedMixin, BaseModel.

Create apps.tenants: Hotel, HotelSettings.

Implement:
- a TenantManager/QuerySet pattern that forces explicit hotel scoping
- a request-level tenant context (middleware or DRF mixin) exposing request.hotel
- database indexes on every hotel foreign key and composite indexes anticipated
  for date-range filtering later
- cross-tenant isolation tests proving Hotel A cannot read Hotel B objects
  even via crafted querysets

Explain explicitly how you prevent a future developer from writing an
unscoped `Model.objects.all()` query by accident.
```

---

## 🟪 Phase 3 — Authentication + RBAC + Hotel Membership

### Django Models
```
User (custom AbstractUser)
HotelMembership(user, hotel, role, status, joined_at)
Role(hotel, name)
Permission(code, name)          # rooms.view, finance.manage, ...
RolePermission(role, permission)
```

### مشاكل Django المتوقعة
- **N+1 كلاسيكي هنا:** حساب صلاحيات المستخدم بيحتاج `Role -> RolePermission -> Permission`. الحل: `prefetch_related("role__rolepermission_set__permission")` أو **caching** نتيجة الصلاحيات في الـSession/Redis لمدة قصيرة (invalidate عند تغيير الـRole).
- **Custom Permission Classes:** بنعمل `HasHotelPermission("rooms.manage")` كـDRF Permission class بتقرأ من `request.user` + `request.hotel` بدل التكرار في كل View.
- **Serializers:** `HotelMembershipSerializer` محتاج nested serializer بسيط لعرض `role.permissions` كـlist بدل ما تعمل join يدوي في الـview.
- **Security:** لازم تفرقة واضحة بين 401 (`IsAuthenticated`) و 403 (`HasHotelPermission`) في exception handler الموحد من Phase 1.
- **Caching:** الصلاحيات المحسوبة (effective permissions) تتخزن في cache key زي `perms:{user_id}:{hotel_id}` وتتمسح عند أي تعديل على Role/RolePermission (استخدم Django signals `post_save`/`post_delete`).

### React
- `core/auth`: login/logout/refresh token flow
- `core/permissions`: hook `useHasPermission("rooms.manage")` بيقرأ من الـuser context

### Prompt
```
Implement Phase 3 only.

Create: User (custom), HotelMembership, Role, Permission, RolePermission.

Implement:
- login/logout/password reset/change endpoints
- multi-hotel membership with an "active hotel" selection endpoint
- a DRF permission class HasHotelPermission(code) evaluated against the
  active hotel context
- effective-permission caching per (user, hotel) in Redis/Django cache,
  invalidated via signals on Role/RolePermission changes
- nested serializer exposing a membership's role and its permission codes
  without N+1 (use prefetch_related)

Return 401 for unauthenticated, 403 for authenticated-but-unauthorized.

React: auth context, token storage strategy, a useHasPermission hook,
and protected route wrapper. Add security + permission tests on both sides.
```

---

## 🟧 Phase 4 — Master Data (Rooms, Customers, Employees, Sources, Languages)

### Django Models
```
RoomType, RoomTypeTranslation, Room
Customer
Employee
BookingSource
Language, HotelLanguage
```

### مشاكل Django المتوقعة
- **Translation tables بدل أعمدة:** `RoomTypeTranslation(room_type, language, name, description)` — لازم `unique_together=("room_type","language")`. الـSerializer هنا هو أول **Nested Serializer** حقيقي في المشروع:
```python
class RoomTypeSerializer(serializers.ModelSerializer):
    translations = RoomTypeTranslationSerializer(many=True, read_only=True)
    class Meta:
        model = RoomType
        fields = [...]
```
  واستخدم `prefetch_related("translations")` في الـSelector لتفادي N+1 (translation لكل RoomType هيبقى query منفصل من غير ده).
- **Validation:** الـ`Room.room_number` لازم يكون unique **جوه الفندق فقط** مش عالميًا:
```python
class Meta:
    constraints = [UniqueConstraint(fields=["hotel","room_number"], name="uniq_room_number_per_hotel")]
```
- **Search/Filtering:** استخدام `django-filter` + full-text search بسيط (`SearchVector`) على `Customer.name/phone/email` بدل `icontains` المتكرر (أبطأ مع البيانات الكبيرة وبدون index).
- **Indexing:** index على `Room.status` (هيتفلتر كتير في الـAvailability لاحقًا)، و index على `Customer.phone`.
- **N+1 في list views:** `RoomSerializer` لو عارض `room_type.name` لازم `select_related("room_type")`.

### React
- CRUD screens بـform validation موحدة (react-hook-form + zod/yup)
- جدول Rooms بفلترة وpagination من السيرفر (مش client-side فلترة لبيانات كبيرة)

### Prompt
```
Implement Phase 4 only.

Create: RoomType, RoomTypeTranslation, Room, Customer, Employee,
BookingSource, Language, HotelLanguage. All tenant-owned models use
HotelOwnedMixin.

Implement:
- nested serializers for RoomType -> translations (prefetch_related, no N+1)
- per-hotel unique constraints (e.g., room_number unique per hotel)
- django-filter based filtering + server-side pagination
- search on Customer (name/phone/email) using an indexed approach,
  not naive icontains on large tables
- select_related for every FK exposed in list serializers

Build React CRUD screens with server-side pagination/filtering and
react-hook-form + schema validation. Do not implement reservations yet.
```

---

## 🟦 Phase 5 — Reservations + Availability Engine + Upgrade

**الهدف:** قلب النظام، وأكتر Phase فيها Concurrency وQuery Optimization.

### Django Models
```
Reservation(customer, booking_source, status, check_in, check_out, ...)
ReservationRoom(reservation, room, room_type, check_in, check_out, nightly_price, nights)
ReservationRoomChange(old_room, new_room, old_price, new_price, difference, reason, changed_by, changed_at)
```

### مشاكل Django المتوقعة (أهم Phase في الموضوع)
- **Availability بدون تكرار بيانات:** overlap query بدل جدول يومي:
```python
ReservationRoom.objects.filter(
    room=room, reservation__status__in=["confirmed","checked_in"]
).filter(check_in__lt=requested_checkout, check_out__gt=requested_checkin)
```
  لازم **composite index** على `(room_id, check_in, check_out)` عشان الاستعلام ده يبقى سريع مع نمو البيانات.
- **Race Condition عند حجز نفس الغرفة من مستخدمين في نفس اللحظة:** لازم:
```python
with transaction.atomic():
    room = Room.objects.select_for_update().get(pk=room_id)
    # ثم يتأكد من الـoverlap جوه نفس الـtransaction
```
  ده أهم استخدام لـ`select_for_update` في المشروع كله.
- **N+1 في قائمة الحجوزات:** `ReservationSerializer` لازم:
```python
Reservation.objects.select_related("customer","booking_source")\
                    .prefetch_related("reservationroom_set__room__room_type")
```
- **Nested Serializer متعدد المستويات:** `Reservation -> rooms (ReservationRoom) -> room -> room_type`. لازم تنتبه إن كل مستوى يتعمله prefetch مناسب وإلا هيبقى N+1 مركب.
- **Validation معقدة:** التحقق من `check_out > check_in`، ومن عدم تعارض الغرف، لازم يكون في **Service Layer** (`ReservationService.create()`) مش في الـSerializer وحده، لأن فيه transactions ومنطق متعدد الخطوات.
- **Price Snapshot:** استخدام `DecimalField(max_digits=10, decimal_places=2)` أبدًا لا `FloatField`.
- **State Machine:** استخدام مكتبة زي `django-fsm` أو تطبيق يدوي بسيط لضبط الانتقالات (`pending→confirmed→checked_in→checked_out`) ومنع انتقال غير صالح.

### React
- Calendar/Availability view بيعتمد على endpoint واحد محسّن (`/availability?room_type=&from=&to=`)
- Reservation Wizard (Customer → Rooms → Payment → Confirm) بخطوات، مع validation في كل خطوة

### Prompt
```
Implement Phase 5 only.

Create: Reservation, ReservationRoom, ReservationRoomChange.

Implement:
- an availability engine using overlap queries (no per-day duplication),
  backed by a composite index on (room_id, check_in, check_out)
- select_for_update + atomic transactions to prevent double-booking race
  conditions
- a ReservationService encapsulating creation, cancellation, no-show,
  check-in, check-out, and room upgrade (with full history in
  ReservationRoomChange)
- a reservation status state machine with explicit valid transitions
- nested serializers (Reservation -> ReservationRoom -> Room -> RoomType)
  fully optimized with select_related/prefetch_related — no N+1
- DecimalField for all monetary/price fields, price snapshot at booking time

Add concurrency tests (simulate two simultaneous bookings for the same room)
and reservation lifecycle tests.

React: build a reservation wizard and an availability calendar view backed
by one optimized endpoint. Handle loading/error/conflict states explicitly.
```

---

## 🟩 Phase 6 — Payments + Finance + Multi-Currency + Closings

### Django Models
```
Payment(reservation, amount, currency, method, date, reference)
PaymentMethod
FinancialTransaction(type, category, amount, currency, method, date)
FinanceCategory
ExchangeRate(hotel, from_currency, to_currency, rate, effective_date)
DailyClosing(hotel, business_date, status, opened_at, closed_at, closed_by)
MonthlyClosing
```

### مشاكل Django المتوقعة
- **Money = DecimalField دايمًا**، وممنوع أي عملية float. استخدم `python-decimal` في كل الحسابات.
- **عدم تحويل العملة تلقائيًا:** الـAggregation في التقارير لازم تتجمع `GROUP BY currency` مش تتجمع مباشرة (`SUM(amount)` لوحده هيبقى غلط لو فيه عملات مختلفة).
- **Celery Background Tasks هنا أول ظهور حقيقي لها:**
  - `close_daily_finance.delay(hotel_id, date)` — مهمة تتشغل تلقائيًا آخر اليوم (Celery Beat) تحسب الملخص وتقفل اليوم.
  - أي عملية تصدير تقرير مالي كبير (PDF/Excel) تتحول لـCelery task عشان متعملش timeout على الـrequest.
- **Caching:** أرصدة/ملخصات اليوم (`DailyClosing` draft) ممكن تتخزن في cache وتتحدث incremental بدل ما تتحسب من الصفر كل مرة، لكن الـsource of truth يفضل الـTransactions نفسها.
- **N+1:** تقرير المدفوعات لازم `select_related("reservation__customer","method")`.
- **Locking بعد الإغلاق:** بعد `DailyClosing.status = closed`، أي محاولة إضافة/تعديل transaction بتاريخ مقفول لازم ترفض على مستوى الـService (مش الـSerializer بس) — استخدم `select_for_update` عند القفل نفسه لمنع Double-closing.

### React
- شاشة Daily Closing بعرض ملخص لحظي (polling أو WebSocket لاحقًا)
- عرض المدفوعات مقسمة بالعملة بشكل واضح، بدون تحويل تلقائي في الواجهة

### Prompt
```
Implement Phase 6 only.

Create: Payment, PaymentMethod, FinancialTransaction, FinanceCategory,
ExchangeRate, DailyClosing, MonthlyClosing.

Rules:
- DecimalField everywhere for money, never float
- preserve original payment currency; aggregate reports by GROUP BY currency
- exchange rates are optional and used only for reporting, never mutate
  original payment records
- once a DailyClosing is closed, block further mutation of that business
  date's transactions at the service layer (not just serializer validation),
  using select_for_update to prevent double-closing race conditions

Celery:
- a scheduled Celery Beat task that closes the previous business day
  automatically if not manually closed
- move heavy financial exports (PDF/Excel) to Celery tasks instead of
  blocking the request

Add financial integrity tests (rounding, currency separation, closing locks)
and N+1-safe payment/finance list serializers.
```

---

## 🟥 Phase 7 — Housekeeping + Maintenance + Complaints + Handover

### Django Models
```
RoomCleaning(room, employee, status, started_at, completed_at, inspected_at)
RoomIssue(room, title, status, priority, assigned_employee, ...)
CustomerComplaint(customer, reservation, category, status, priority, ...)
```

### مشاكل Django المتوقعة
- **Workflow enforcement على مستوى الـService:** منع `Room.status = AVAILABLE` لو فيه `RoomIssue` مفتوح `blocking=True` — لازم يتحقق داخل `RoomService.mark_available()` مش مجرد اختيار في الـfrontend.
- **Signals حساسة:** استخدام `post_save` على `Reservation` (عند checkout) لإنشاء `RoomCleaning` تلقائيًا — لكن احذر من **Signals المتشابكة** (signal بينده signal) لأنها بتصعب الـdebugging؛ الأفضل استدعاء صريح من داخل `CheckoutService` بدل الاعتماد الكامل على Signals.
- **Notifications Trigger:** إنشاء `RoomIssue` بأولوية عالية لازم يبعت إشعار فورًا — هنا أول ربط مع Celery/Notifications (Phase 8) فـ decouple عن طريق **Django signal يطلق Celery task** بدل استدعاء مباشر متزامن.
- **Indexing:** index على `RoomIssue.status` و`priority` (query دايمة: "كل المشاكل المفتوحة عالية الأولوية").
- **Serializer:** `RoomSerializer` ممكن يحتاج nested field بيقول "هل فيه blocking issue؟" (`SerializerMethodField`) — احذر إنه يعمل query إضافي لكل صف؛ الحل: annotate على الـqueryset (`Exists(RoomIssue.objects.filter(room=OuterRef("pk"), blocking=True, status__in=[...]))`) بدل حساب Python-side لكل عنصر (تفادي N+1).

### React
- Kanban بسيط لحالة الغرف (Dirty/Cleaning/Inspected/Available)
- شاشة Maintenance بفلترة بالأولوية

### Prompt
```
Implement Phase 7 only.

Create: RoomCleaning, RoomIssue, CustomerComplaint.

Implement:
- workflows enforced in service layer (a room cannot become AVAILABLE while
  a blocking unresolved RoomIssue exists)
- an efficient "has_blocking_issue" flag on room querysets using
  annotate(Exists(...)) rather than a per-row SerializerMethodField query
- explicit service calls for cross-domain effects (checkout -> create
  cleaning task) instead of chained signals, to keep the flow debuggable
- a Django signal that enqueues a Celery notification task when a
  high-priority RoomIssue is created (decoupled from the request-response cycle)
- indexes on RoomIssue.status and priority

Add role-based access, tenant isolation, and workflow tests
(e.g., attempting to free a room with a blocking issue must fail).
```

---

## 🟪 Phase 8 — Documents + Notifications + Reminders

### Django Models
```
Document(reservation, type, file, language)
Notification(user/hotel, type, channel, payload, read_at)
ReminderRule(hotel, type, schedule, active)
```

### مشاكل Django المتوقعة
- **Celery الحقيقي بيبدأ هنا بجد:**
  - توليد PDF (WeasyPrint/xhtml2pdf) دايمًا Celery task، مش synchronous، لأن توليد PDF بطيء ولازم مايوقفش الـrequest.
  - Celery Beat لجدولة الـReminders (`check-in tomorrow`, `unpaid balance`) — task دورية كل ساعة تفحص القواعد وتنشئ Notification/تبعت Email.
- **Provider Abstraction:** واجهة `NotificationChannel` (interface) عشان تقدر تبدل Email/SMS/WhatsApp بدون تعديل الكود الأساسي — Strategy pattern بسيط.
- **Idempotency:** الـReminder tasks لازم تتأكد إنها مش هتبعت نفس التنبيه مرتين (unique constraint أو "sent_at" check) — مشكلة شائعة جدًا مع Celery Beat.
- **Caching:** locale/translation resolution للـPDF (اللغة الافتراضية للفندق) تتخزن cache بسيطة عشان متتحسبش من قاعدة البيانات كل مرة.
- **File Storage:** استخدام `django-storages` (S3 أو المكافئ) بدل الحفظ المحلي في production، وده قرار لازم يتاخد من الـPhase دي.

### React
- In-app notification bell (polling كل فترة أو WebSocket اختياري لاحقًا)
- عرض/تحميل الـDocuments (Confirmation PDF) بلغة العميل

### Prompt
```
Implement Phase 8 only.

Create: Document, Notification, ReminderRule.

Implement:
- localized booking confirmation PDF generation as a Celery task (not
  synchronous in the request)
- Celery Beat scheduled tasks scanning ReminderRules and creating
  notifications, with idempotency guards so a reminder is never sent twice
- a NotificationChannel abstraction (in-app/email now, SMS/WhatsApp behind
  the same interface for later)
- file storage via django-storages (S3-compatible), not local disk, for production
- caching of hotel default-locale resolution used during document generation

Add tests for: PDF task success/failure handling, reminder idempotency,
and notification delivery abstraction.

React: notification center with polling, and a documents list per reservation
with download links.
```

---

## 🟩 Phase 9 — SaaS Features + Subscriptions

### Django Models
```
Feature, FeatureCategory
SubscriptionPlan, PlanFeature
Subscription(hotel, plan, status, trial_ends_at, ...)
HotelFeatureOverride(hotel, feature, enabled, limits)
```

### مشاكل Django المتوقعة
- **FeatureService هو أهم جزء هنا:** قرار الوصول = `Platform State + Plan + Override + Permission + Tenant`. لازم **caching قوي** (Redis) لكل `(hotel_id)` عشان الـcheck ده هيتنفذ على كل تقريبًا كل Request — مع invalidation عند تغيير الـSubscription/Override (`post_save` signals).
- **Custom DRF Permission/Decorator:** `RequiresFeature("finance")` تتحط جنب `HasHotelPermission` مش بدالها.
- **Limits Enforcement (مثلاً max_rooms):** لازم تتحقق في الـService عند الإنشاء (`RoomService.create()` يتأكد من `Room.objects.filter(hotel=hotel).count() < limit`) — وده query لازم يتعمله caching بسيط أو annotate بدل count متكرر على كل عملية إنشاء لو الترافيك عالي.
- **Query Optimization:** جدول `PlanFeature` غالبًا صغير وثابت نسبيًا → مرشح ممتاز لـ**caching طويل المدى** (`cache.get_or_set`).

### React
- `FeatureGuard` component + `useFeature("analytics")` hook — للـUX فقط، التحقق الحقيقي في الباك.

### Prompt
```
Implement Phase 9 only.

Create: Feature, FeatureCategory, SubscriptionPlan, PlanFeature,
Subscription, HotelFeatureOverride.

Implement a centralized FeatureService resolving effective access from:
platform state -> plan -> hotel override -> user permission -> tenant scope.

Cache the resolved feature set per hotel in Redis, invalidated via signals
on Subscription/HotelFeatureOverride changes.

Implement:
- a RequiresFeature(code) DRF permission/decorator composable with
  HasHotelPermission
- limit enforcement (max_users, max_rooms) inside creation services,
  not just serializer validation
- caching of relatively static PlanFeature lookups

React: FeatureGuard component and useFeature hook for UX only — document
clearly that Django remains the real enforcement boundary. Add SaaS admin
screens to toggle features per hotel.
```

---

## 🟧 Phase 10 — Translation System + Hotel Website

### Django Models
```
Language, HotelLanguage
RoomTypeTranslation (already exists, extend pattern to other content)
Website, WebsitePage, WebsiteSection
```

### مشاكل Django المتوقعة
- **Locale Resolution + Fallback:** middleware/utility بيحدد اللغة من (query param → user preference → hotel default → English) — لازم تتخزن cache بسيطة لكل request عشان متتكررش الحسابات.
- **Domain/Subdomain Resolution لازم تكون Server-Side حصريًا:** ممنوع الكلاينت يبعت `hotel_id` في request للـwebsite العام؛ الـHotel يتحدد من الـHost header فقط (middleware مخصص)، وإلا فتحنا ثغرة Cross-Tenant خطيرة.
- **N+1 على صفحة الموقع العام:** `WebsitePage -> WebsiteSection -> translations` — استخدم `prefetch_related` متعدد المستويات، وفكر في **Caching الصفحة كاملة** (`cache_page` أو fragment caching) لأن محتوى الموقع بيتغير نادرًا مقارنة بزيارات القراءة.
- **إعادة استخدام الـServices الموجودة:** الـWebsite لازم يستدعي نفس `AvailabilityService`/`ReservationService` من Phase 5، مش نسخة منفصلة — وإلا هيبقى فيه ازدواجية منطق خطيرة.

### React (public site جزء منفصل، لكن يشارك core)
- صفحة عامة (يفضل SSR/Next.js لو الـSEO مهم، أو React عادي لو الأولوية للسرعة في البناء)
- استهلاك نفس الـAvailability API من غير تكرار منطق

### Prompt
```
Implement Phase 10 only.

Create: Language, HotelLanguage, Website, WebsitePage, WebsiteSection,
plus translation tables for any remaining domain content (not one language
column per field).

Implement:
- server-side-only hotel resolution from the request Host/subdomain
  (never trust a client-supplied hotel id on public endpoints)
- locale resolution with fallback (query param -> user pref -> hotel default -> base language)
- multi-level prefetch_related for Website -> Pages -> Sections -> translations
- fragment or page-level caching for the public site given its low write frequency
- the public website reusing the existing AvailabilityService/ReservationService
  from Phase 5, with no duplicated booking logic

Add tests proving the public site can never leak another hotel's data via
a manipulated request.
```

---

## 🟦 Phase 11 — Reports + Analytics

### Django مشاكل متوقعة (Phase دي هي اختبار حقيقي للـQuery Optimization)
- **Aggregation على مستوى الـDatabase مش Python:** استخدم `annotate()`, `aggregate()`, `Sum`, `Count`, `Avg` بدل ما تلف على الـQuerySet في Python وتجمع يدويًا.
- **Indexing حرج هنا:** أي عمود هيتفلتر بيه تقرير (تاريخ، حالة، نوع غرفة، مصدر حجز) لازم index، وأفضل composite index على `(hotel_id, date_field)` لأن كل تقرير هيبدأ بفلترة بالفندق والتاريخ.
- **N+1 في التقارير المجمّعة:** لو التقرير محتاج تفاصيل مع الإجمالي، افصل بين "Summary query" (aggregate واحد) و"Detail query" (paginated list) — متحاولش ترجعهم مع بعض في structure متداخل تقيل.
- **Caching نتائج التقارير الثقيلة:** تقرير الشهر الماضي مثلاً نتيجته ثابتة عمليًا → cache لمدة ساعات مع مفتاح يتضمن الفلاتر (`report:occupancy:{hotel}:{from}:{to}`).
- **Celery للتقارير الكبيرة:** أي تصدير PDF/CSV لفترة طويلة يتحول لـCelery task مع endpoint لمتابعة الحالة (polling) بدل ما يعلّق الـrequest.
- **قرار Denormalization:** لو بعد الـProfiling (باستخدام django-silk) لقينا استعلام تقرير بطيء فعلاً رغم التحسين، وقتها بس نضيف `MetricSnapshot` model محدثة عبر Celery task دورية — مش من البداية.

### React
- Dashboard بيستهلك endpoints منفصلة للـKPIs (كل كارت = query خفيف) بدل endpoint ضخم واحد بيحسب كل حاجة مرة واحدة.
- Charts (recharts) مع date-range picker، وloading/error/empty state لكل chart.

### Prompt
```
Implement Phase 11 only.

Build report/analytics services over existing source-of-truth data using
database-level aggregation (annotate/aggregate), not Python-side loops.

Implement:
- composite indexes on (hotel_id, date_field) for every report's main filter path
- separated summary (aggregate) vs detail (paginated) queries
- caching of heavy/historical report results keyed by hotel+filters
- Celery-based async export for CSV/PDF with a status-polling endpoint
- profiling notes: only introduce a MetricSnapshot denormalized table if
  profiling (e.g. via django-silk) proves the live aggregation is too slow

Enforce permissions and Feature Entitlements from Phase 9 on every report endpoint.

React: dashboard with independent lightweight KPI endpoints per card, and
charts with date-range filtering and per-chart loading/error/empty states.
```

---

## 🟦 Phase 12 — Security + Testing + Performance + Production

### Django — القائمة النهائية للمراجعة
| المجال | الإجراء |
|---|---|
| N+1 | مراجعة كل Serializer بـ`django-silk`/`nplusone` package، وتأكيد `select_related`/`prefetch_related` في كل مكان |
| Indexing | مراجعة شاملة لكل الجداول الكبيرة (Reservation, Payment, FinancialTransaction, Notification) |
| Caching | مراجعة كل الـcache keys وinvalidation logic (خصوصًا Feature Entitlements والتقارير) |
| Celery | مراجعة كل الـTasks: retries, `acks_late`, dead-letter handling, idempotency |
| Serializers/Validation | تأكيد إن الـbusiness validation في الـService مش الـSerializer وحده، والـSerializer بيتحقق من الشكل فقط |
| Security | Rate limiting (`django-ratelimit`/DRF throttling)، CORS، CSRF، secrets عبر environment/secret manager، audit logging لكل عملية حساسة (مالية/صلاحيات) |
| Tenant Isolation | Test suite كامل يحاول اختراق كل endpoint بـhotel_id مختلف |
| DB | مراجعة migrations، `CONN_MAX_AGE`، connection pooling (pgbouncer لو الحمل عالي) |

### Testing
- Unit + Integration + API + E2E + Concurrency (reservation race) + Financial Integrity + Tenant Isolation + RBAC + Feature Entitlement

### Production
- CI/CD (GitHub Actions مثلاً) → staging → production
- Monitoring (Sentry للأخطاء)، Logging مركزي، Backups (DB يوميًا)، Rollback strategy، Celery workers منفصلين عن web workers

### Prompt
```
Implement Phase 12 only.

Perform a full audit and hardening pass:
- run N+1 detection (django-silk/nplusone) across every serializer/viewset
  and fix remaining unoptimized queries
- review and complete indexing across Reservation, Payment,
  FinancialTransaction, Notification, and any high-traffic table
- review all cache keys and invalidation logic for correctness
- review all Celery tasks for retries, acks_late, and idempotency
- confirm business validation lives in services, not just serializers
- implement rate limiting, CORS, CSRF hardening, secret management,
  and audit logging for sensitive operations

Testing: unit, integration, API, E2E, tenant isolation, RBAC, feature
entitlement, reservation concurrency, and financial integrity test suites.

Production: CI/CD pipeline, staging environment, monitoring (error tracking),
centralized logging, automated backups, rollback strategy, and separated
Celery worker deployment from the web process.

Report a final checklist of what was verified and any residual risks.
```

---

## 🔐 القاعدة الذهبية لأي Feature جديدة بعد كده

```
MODEL → MIGRATION → SELECTOR → SERVICE → SERIALIZER
→ PERMISSION → FEATURE CHECK → TENANT SCOPE → BUSINESS RULE
→ API → REACT UI → TESTS
```

لو حبيت أوسّع أي Phase من الـ12 دول بتفاصيل أعمق (كود كامل للـModels/Services/Celery tasks الخاصة بيها)، قولي رقم الـPhase وهكتبهولك كامل.
