# Phase 7 — Housekeeping + Maintenance + Complaints + Integration Completions
# المرحلة السابعة — الإشراف الداخلي والصيانة والشكاوى واستكمال الربط المعماري

---

## Table of Contents

1. [Overview](#1-overview)
2. [Integration Completions](#2-integration-completions)
3. [Models](#3-models)
4. [Housekeeping Workflow](#4-housekeeping-workflow)
5. [Maintenance Blocking Pattern](#5-maintenance-blocking-pattern)
6. [Signal Architecture](#6-signal-architecture)
7. [N+1 Prevention for Room List with Blocking Flag](#7-n1-prevention-for-room-list-with-blocking-flag)
8. [Complaints Lifecycle](#8-complaints-lifecycle)
9. [Celery Tasks](#9-celery-tasks)
10. [API Endpoints](#10-api-endpoints)
11. [Permissions](#11-permissions)
12. [Tests Summary](#12-tests-summary)
13. [Files Changed](#13-files-changed)
14. [Migrations](#14-migrations)

---

## 1. Overview | ١. نظرة عامة شاملة على العمليات التشغيلية اليومية

> [!NOTE]
> 💡 **شرح باللغة العربية (Overview):**
> تمثل المرحلة السابعة الطبقة الإدارية والتشغيلية المباشرة (Operational Management Layer) لمنصة إدارة الفنادق.
> تقدم هذه المرحلة ثلاثة تطبيقات رئيسية: `housekeeping` (إدارة دورة حياة تنظيف الغرف)، `maintenance` (إدارة بلاغات الصيانة والأعطال المانعة)، و `complaints` (إدارة ومتابعة شكاوى النزلاء).
> بالإضافة إلى ذلك، تتميز هذه المرحلة بإتمام **خطافي الربط المعلقين** من المرحلتين الرابعة والخامسة، مما يحقق التكامل الكامل والمحكم بين دورة حياة الغرف والحجوزات والصيانة.

Phase 7 implements the **operational management layer** of the Hotel SaaS platform. It introduces three new Django applications — `housekeeping`, `maintenance`, and `complaints` — that together form the backbone of hotel daily operations. Beyond introducing new functionality, Phase 7 is architecturally significant because it **completes two integration placeholders** that were intentionally left as stubs in Phases 4 and 5, allowing those earlier phases to be tested and shipped independently while the downstream dependencies were not yet built.

### What Phase 7 Delivers

| Area | Description |
|---|---|
| **Housekeeping** | Full workflow for cleaning task lifecycle — creation at checkout, assignment, progress tracking, and supervisor inspection |
| **Maintenance** | Issue reporting and tracking with a `blocking` flag that prevents rooms from being marked available until resolved |
| **Complaints** | Customer complaint intake, assignment to staff, and resolution with audit timestamps |
| **Integration Completions** | `_check_no_blocking_issues()` in `rooms/services.py` and `_create_cleaning_tasks()` in `reservations/services.py` are now fully implemented |

### System Connectivity

Phase 7 connects all previously built operational modules:

- The **Rooms** module (`Phase 4`) now has a real blocking check when transitioning room status to `AVAILABLE`.
- The **Reservations** module (`Phase 5`) now triggers real cleaning task creation on checkout.
- The **Maintenance** module blocks room availability through the shared `RoomService` interface.
- The **Housekeeping** module drives the room back to `AVAILABLE` status after a successful inspection.
- **Celery** (`Phase 6` infrastructure) is consumed here for the first time in a business-logic context — dispatching high-priority maintenance notifications asynchronously.

This phase completes the **backend feature set for hotel daily operations**, leaving only reporting, analytics, and billing for subsequent phases.

---

## 2. Integration Completions | ٢. استكمال نقاط الربط المعمارية المعلقة من المراحل السابقة

> [!IMPORTANT]
> 💡 **شرح اكتمال الربط المعماري:**
> في المرحلتين 4 و 5، تم وضع دوال تمهيدية (Stubs/Placeholders) لتمكين اختبار تلك المراحل بشكل مستقل.
> في هذه المرحلة تم تفعيل التنفيذ الفعلي الكامل لهذين الخطافين:

> [!IMPORTANT]
> Two function stubs left as placeholders in Phases 4 and 5 are now **fully implemented** in Phase 7. These completions are not additive features — they are **correctness fixes** that close a known gap in the system's operational logic. All existing tests from Phases 4 and 5 continue to pass because the placeholder implementations were designed to be non-breaking drop-ins.

---

### A. `rooms/services.py` — `_check_no_blocking_issues()` | خطاف فحص الأعطال المانعة لإتاحة الغرفة

> 💡 **الشرح الفني:** تم تفعيل الدالة لتبحث في جدول `RoomIssue`. إذا كان هناك أي عطل يحمل خاصية `blocking=True` وما زال مفتوحاً أو قيد الإصلاح، تمنع الدالة تحويل الغرفة إلى `AVAILABLE` وترفع خطأ `ValidationError` فورياً.

#### Background (Phase 4)

In Phase 4, `RoomService.mark_available()` needed to guard against marking a room as `AVAILABLE` when an unresolved maintenance issue was blocking it. However, the `maintenance` app did not yet exist, so the `RoomIssue` model was unavailable. The function was written as a placeholder that **always returned `True`**, effectively disabling the check:

```python
# Phase 4 placeholder — intentionally incomplete
def _check_no_blocking_issues(room):
    # TODO: implement in Phase 7 once RoomIssue model is available
    return True
```

This allowed `mark_available()` to be tested and the Rooms module to be shipped without a hard dependency on the Maintenance module.

#### Phase 7 Implementation

The function is now fully implemented. It queries the `RoomIssue` model for any open or in-progress blocking issues on the given room and raises a `RoomBlockedError` if any are found:

```python
def _check_no_blocking_issues(room):
    has_blocking = RoomIssue.objects.filter(
        room=room,
        blocking=True,
        status__in=[IssueStatus.OPEN, IssueStatus.IN_PROGRESS],
    ).exists()
    if has_blocking:
        raise RoomBlockedError(
            f"Room {room.room_number} has open blocking maintenance issues."
        )
```

`RoomService.mark_available()` calls `_check_no_blocking_issues(room)` **before** changing the room status:

```python
class RoomService:
    @staticmethod
    def mark_available(room):
        _check_no_blocking_issues(room)  # raises RoomBlockedError if blocked
        room.status = RoomStatus.AVAILABLE
        room.save(update_fields=["status"])
```

**Key design properties:**

- Uses `.exists()` — a single optimised SQL query with early termination; does not fetch full model instances.
- Checks `status__in=[OPEN, IN_PROGRESS]` — a resolved or closed issue no longer blocks the room.
- Raises `RoomBlockedError` (a custom domain exception) rather than returning a boolean, so callers cannot silently ignore the failure.

---

### B. `reservations/services.py` — `_create_cleaning_tasks()` | خطاف إنشاء مهام التنظيف التلقائي عند المغادرة

> 💡 **الشرح الفني:** فور قيام النزيل بعمل مغادرة (`check_out`)، تستدعي الدالة مباشرة إنشاء سجلات `RoomCleaning` لكل غرف الحجز بحالة `PENDING` لتحويلها إلى قسم الإشراف الداخلي.

#### Background (Phase 5)

In Phase 5, the checkout flow needed to trigger housekeeping task creation for each checked-out room. The `housekeeping` app and `RoomCleaning` model did not yet exist, so the function body was left as `pass`:

```python
# Phase 5 placeholder — intentionally incomplete
def _create_cleaning_tasks(reservation):
    pass  # TODO: implement in Phase 7 once RoomCleaning model is available
```

The checkout service called this function correctly, so the call site required no changes in Phase 7.

#### Phase 7 Implementation

The function now creates a `RoomCleaning` record for each active room in the reservation:

```python
def _create_cleaning_tasks(reservation):
    for res_room in reservation.reservation_rooms.filter(is_deleted=False):
        RoomCleaning.objects.create(
            hotel=reservation.hotel,
            room=res_room.room,
            status=CleaningStatus.PENDING,
            reservation=reservation,
            scheduled_date=date.today(),
        )
```

**Key design properties:**

- Filters `is_deleted=False` to skip soft-deleted reservation rooms (consistent with the soft-delete pattern established in Phase 5).
- Sets `scheduled_date=date.today()` — cleaning is always scheduled for the day of checkout.
- Links `reservation` on `RoomCleaning` for full audit traceability — housekeeping staff can see which guest's checkout triggered the task.
- Sets initial `status=CleaningStatus.PENDING` — the task enters the housekeeping queue immediately.

#### Design Decision: Explicit Call vs. Signal | قرار التصميم: الاستدعاء الصريح مقابل إشارات دجانجو

> 💡 **التعليل الهندسي:** تفضيل الاستدعاء الصريح المباشر داخل كود المغادرة بدلاً من استخدام `post_save` signals يمنع ظاهرة (Spaghetti Signals) ويجعل مسار تنفيذ الأكواد واضحاً وسهل التتبع والاختبار والصيانة.

`_create_cleaning_tasks()` is called **explicitly** from the checkout service rather than via a Django `post_save` signal on the `Reservation` model. This is intentional:

| Approach | Rationale |
|---|---|
| **Explicit call (chosen)** | Easier to test — the test simply calls checkout and asserts `RoomCleaning` objects were created, no signal mocking required |
| **Explicit call (chosen)** | No hidden side effects — the causal chain is visible by reading the checkout function |
| **Signal (rejected)** | Signals fire on every `save()`, including admin edits and bulk updates, creating unintended cleaning tasks |
| **Signal (rejected)** | Harder to trace in production — the connection between checkout and cleaning creation is implicit |

---

## 3. Models

### 3.1 `RoomCleaning` (`housekeeping/models.py`) | نموذج مهام الإشراف الداخلي وتنظيف الغرف

> 💡 **شرح المودل بالعربية (Room Cleaning Task):**
> يمثل مهمة تنظيف الغرفة. يتم إنشاؤه تلقائياً عند المغادرة أو يدوياً من المشرف.
> يمر بأربع مراحل واضحة: `PENDING` (معلق) → `IN_PROGRESS` (جاري التنظيف) → `COMPLETED` (تم التنظيف) → `INSPECTED` (تم الفحص والاعتماد).

Represents a single cleaning task for a hotel room, typically created at guest checkout.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key, auto-generated |
| `hotel` | `ForeignKey(Hotel)` | Non-nullable; cascade delete |
| `room` | `ForeignKey(Room)` | Non-nullable; cascade delete |
| `reservation` | `ForeignKey(Reservation)` | **Nullable** — cleaning tasks can be created manually without a reservation |
| `assigned_to` | `ForeignKey(User)` | **Nullable** — set when a housekeeper is assigned |
| `status` | `CharField` | Choices: `CleaningStatus` (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `INSPECTED`) |
| `scheduled_date` | `DateField` | Date the cleaning is scheduled to occur |
| `started_at` | `DateTimeField` | **Nullable** — set when status transitions to `IN_PROGRESS` |
| `completed_at` | `DateTimeField` | **Nullable** — set when status transitions to `COMPLETED` |
| `inspected_at` | `DateTimeField` | **Nullable** — set when status transitions to `INSPECTED` |
| `notes` | `TextField` | Blank allowed — optional freeform notes from the housekeeper or supervisor |
| `created_at` | `DateTimeField` | Auto-set on creation |

**`CleaningStatus` choices:**

```python
class CleaningStatus(models.TextChoices):
    PENDING     = "PENDING",     "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED   = "COMPLETED",   "Completed"
    INSPECTED   = "INSPECTED",   "Inspected"
```

---

### 3.2 `RoomIssue` (`maintenance/models.py`) | نموذج بلاغات وأعطال الصيانة

> 💡 **شرح المودل بالعربية (Room Issue / Work Order):**
> يمثل عطلاً أو بلاغ صيانة للغرفة. يحتوي على درجة الأهمية (`low`, `medium`, `high`, `critical`)، وعلامة `blocking=True` التي تحظر استخدام الغرفة للحجوزات حتى إصلاح العطل.

Represents a maintenance issue reported for a specific room. The `blocking` flag integrates with the room availability system.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key, auto-generated |
| `hotel` | `ForeignKey(Hotel)` | Non-nullable; cascade delete |
| `room` | `ForeignKey(Room)` | Non-nullable; cascade delete |
| `reported_by` | `ForeignKey(User)` | Non-nullable — the staff member who reported the issue |
| `assigned_to` | `ForeignKey(User)` | **Nullable** — set when a maintenance technician is assigned |
| `title` | `CharField` | Short description of the issue |
| `description` | `TextField` | Full description of the issue |
| `priority` | `CharField` | Choices: `IssuePriority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`); `db_index=True` |
| `blocking` | `BooleanField` | Default `False` — when `True`, prevents the room from being marked `AVAILABLE` |
| `status` | `CharField` | Choices: `IssueStatus` (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`) |
| `resolution_notes` | `TextField` | Blank allowed — notes filled in when resolving the issue |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `resolved_at` | `DateTimeField` | **Nullable** — set when status transitions to `RESOLVED` or `CLOSED` |

**`IssuePriority` choices:**

```python
class IssuePriority(models.TextChoices):
    LOW      = "LOW",      "Low"
    MEDIUM   = "MEDIUM",   "Medium"
    HIGH     = "HIGH",     "High"
    CRITICAL = "CRITICAL", "Critical"
```

**`IssueStatus` choices:**

```python
class IssueStatus(models.TextChoices):
    OPEN        = "OPEN",        "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED    = "RESOLVED",    "Resolved"
    CLOSED      = "CLOSED",      "Closed"
```

**Database index on `priority`:** The `priority` field carries `db_index=True` because maintenance dashboards frequently filter or order by priority. This avoids sequential scans on large issue tables.

**Post-save signal:** A `post_save` signal is registered on `RoomIssue`. When a newly created issue has `priority=HIGH` or `priority=CRITICAL`, the signal dispatches the `notify_high_priority_issue` Celery task. See [Section 6](#6-signal-architecture) for full details.

---

### 3.3 `CustomerComplaint` (`complaints/models.py`) | نموذج شكاوى النزلاء ومتابعتها

> 💡 **شرح المودل بالعربية (Customer Complaint):**
> يوثق شكاوى النزلاء مع تصنيف نوع الشكوى (نظافة، ضوضاء، فواتير، خدمات)، وتحديد الأولوية، وربطها بالموظف المسؤول، مع توثيق ملاحظات الحل النهائي.

Represents a complaint raised by a hotel customer, optionally linked to a reservation for context.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | `UUIDField` | Primary key, auto-generated |
| `hotel` | `ForeignKey(Hotel)` | Non-nullable; cascade delete |
| `customer` | `ForeignKey(User)` | Non-nullable — the guest who raised the complaint |
| `reservation` | `ForeignKey(Reservation)` | **Nullable** — links the complaint to a specific stay for context |
| `assigned_to` | `ForeignKey(User)` | **Nullable** — the staff member handling the complaint |
| `title` | `CharField` | Short summary of the complaint |
| `description` | `TextField` | Full description of the complaint |
| `priority` | `CharField` | Choices: `ComplaintPriority` (`LOW`, `MEDIUM`, `HIGH`) |
| `status` | `CharField` | Choices: `ComplaintStatus` (`OPEN`, `IN_PROGRESS`, `RESOLVED`) |
| `resolution_notes` | `TextField` | Blank allowed — filled in when resolving the complaint |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `resolved_at` | `DateTimeField` | **Nullable** — set when status transitions to `RESOLVED` |

**`ComplaintStatus` choices:**

```python
class ComplaintStatus(models.TextChoices):
    OPEN        = "OPEN",        "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED    = "RESOLVED",    "Resolved"
```

---

## 4. Housekeeping Workflow | ٤. دورة عمل قسم الإشراف الداخلي (Workflow)

> 💡 **شرح دورة التنظيف:** لا يمكن للغرفة أن تعود لحالة `AVAILABLE` إلا بعد أن يقوم المشرف بعملية الفحص والاعتماد (`inspect`) بنجاح، بشرط ألا يكون عليها بلاغ صيانة مانع.

### Status Transition Diagram

```
PENDING
   │
   │  assign housekeeper (assigned_to set)
   ▼
IN_PROGRESS
   │
   │  housekeeper marks done
   ▼
COMPLETED
   │
   │  supervisor inspects room
   ▼
INSPECTED ──► RoomService.mark_available(room)
                    │
                    ├─ No blocking issues ──► Room status: AVAILABLE ✓
                    │
                    └─ Blocking issue found ──► Room status: MAINTENANCE ✗
                         (RoomBlockedError raised and caught)
```

### Transition Rules

| Transition | Trigger | Side Effects |
|---|---|---|
| `PENDING → IN_PROGRESS` | Housekeeper assigned and starts task | `started_at` set to `timezone.now()` |
| `IN_PROGRESS → COMPLETED` | Housekeeper marks room as clean | `completed_at` set to `timezone.now()` |
| `COMPLETED → INSPECTED` | Supervisor inspects and approves | `inspected_at` set; `mark_available()` called |

### Inspection Transition Implementation

The inspection step is the critical integration point between housekeeping and the rooms module:

```python
def inspect_cleaning(cleaning, inspected_by):
    if cleaning.status != CleaningStatus.COMPLETED:
        raise InvalidTransitionError("Can only inspect completed cleanings.")
    cleaning.status = CleaningStatus.INSPECTED
    cleaning.inspected_at = timezone.now()
    cleaning.save()
    try:
        RoomService.mark_available(cleaning.room)
    except RoomBlockedError:
        cleaning.room.status = RoomStatus.MAINTENANCE
        cleaning.room.save()
```

**Design notes:**

- `InvalidTransitionError` is raised for illegal state transitions — callers receive a clear, domain-specific error rather than a generic `ValueError`.
- `RoomBlockedError` is caught at the inspection level. The cleaning task is still marked `INSPECTED` (the inspector did their job), but the room is moved to `MAINTENANCE` status to signal that a maintenance issue must be resolved before the room re-enters service.
- The `inspected_by` parameter is available for audit logging (not shown in snippet above for brevity, but stored in the audit trail).

---

## 5. Maintenance Blocking Pattern | ٥. نمط الأعطال المانعة لحجز الغرف (Blocking Pattern)

> 💡 **شرح نمط الحظر:** الأمان الفندقي يقتضي عدم بيع أي غرفة بها عطل تسريب مياه أو تكييف معطل للنزلاء.
> لذلك، حتى لو تم تنظيف الغرفة، لا يسمح النظام بتحويلها لمتاحة طالما وجد بلاغ مانع مفتوح.

### What "Blocking" Means

A `RoomIssue` with `blocking=True` signals that the reported problem renders the room **unfit for guest occupation**. Examples: broken HVAC system, plumbing leak, fire suppression fault. The room must not be reassigned to a new guest until the issue is resolved and a housekeeping inspection confirms the room is ready.

### Blocking Check Logic

`_check_no_blocking_issues()` is called by `RoomService.mark_available()` every time a room is about to be set to `AVAILABLE`. It checks for the existence of any `RoomIssue` that satisfies all three conditions:

1. Belongs to the target room.
2. Has `blocking=True`.
3. Has `status` in `[OPEN, IN_PROGRESS]` — i.e., not yet resolved.

If such an issue exists, `RoomBlockedError` is raised and the room **remains in its current status** (`CLEANING` or `MAINTENANCE`).

### Important: No Auto-Transition on Issue Resolution

When a blocking `RoomIssue` is moved to `RESOLVED` or `CLOSED`, the system does **not** automatically mark the room as `AVAILABLE`. This is a deliberate safety decision:

> Resolving a maintenance issue removes the technical block, but a housekeeping inspection is still required before the room re-enters the guest-facing inventory. A technician may have fixed the plumbing but left the room in disarray. The inspector confirms both that the issue is resolved and that the room is physically clean and presentable.

The flow to return a room to `AVAILABLE` after a blocking issue always passes through housekeeping inspection.

### End-to-End Flow

```
Guest Checkout (Phase 5)
        │
        ▼
_create_cleaning_tasks()
        │ creates RoomCleaning (status=PENDING)
        ▼
Housekeeping Assignment
        │ assigned_to set, status=IN_PROGRESS
        ▼
Housekeeper Completes Cleaning
        │ status=COMPLETED, completed_at set
        ▼
Supervisor Inspects Room
        │ status=INSPECTED, inspected_at set
        ▼
RoomService.mark_available(room) called
        │
        ├──[No blocking issues]──► Room status = AVAILABLE ✓
        │
        └──[Blocking issue OPEN/IN_PROGRESS]
                │
                └──► RoomBlockedError raised
                          │
                          └──► Room status = MAINTENANCE ✗
                                   (issue must be resolved + re-inspected)
```

---

## 6. Signal Architecture | ٦. معمارية الإشارات وإشعارات الطوارئ الفورية

> 💡 **شرح معمارية الإشارات:** عند إنشاء بلاغ صيانة بأولوية حرجة (`critical`) أو عالية (`high`)، تطلق إشارة `post_save` مهمة غير متزامنة في Celery (`notify_high_priority_issue.delay()`) لإشعار الإدارة فوراً دون إبطاء استجابة واجهة المستخدم.

### `post_save` Signal on `RoomIssue`

A Django `post_save` signal is registered on the `RoomIssue` model in `maintenance/signals.py`. When a new `RoomIssue` is created with `priority=HIGH` or `priority=CRITICAL`, it immediately dispatches the `notify_high_priority_issue` Celery task:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=RoomIssue)
def room_issue_post_save(sender, instance, created, **kwargs):
    if created and instance.priority in [IssuePriority.HIGH, IssuePriority.CRITICAL]:
        notify_high_priority_issue.delay(instance.id)
```

**Key properties:**

- `created=True` guard — the signal only fires on initial creation, not on subsequent updates (e.g., when a technician updates `resolution_notes`). This prevents duplicate notifications.
- `.delay()` — dispatches the task to Celery asynchronously. The HTTP request that created the issue completes without waiting for the notification to be sent.
- Signal receivers are registered in `maintenance/apps.py` via the `ready()` hook to ensure they are loaded when Django starts.

### Why Celery Instead of a Direct Notification Call

| Concern | Explanation |
|---|---|
| **Retry on failure** | If the notification service (email provider, push notification gateway) is temporarily unavailable, Celery retries the task up to `max_retries=3` with exponential backoff. A direct call would silently fail or require complex retry logic inside the request cycle. |
| **No request failure** | The HTTP POST that creates the `RoomIssue` completes immediately with a `201 Created` response. The notification is fully decoupled — a slow or unavailable notification service never causes a timeout for the API client. |
| **Observability** | Celery tasks appear in Flower (the Celery monitoring dashboard) and in structured logs. Operations teams can see how many notifications were sent, how many retried, and inspect failure reasons — none of which is possible with a direct in-process call. |
| **Testability** | In tests, `notify_high_priority_issue.delay` can be mocked or replaced with `task_always_eager=True` without modifying the signal code. |

---

## 7. N+1 Prevention for Room List with Blocking Flag | ٧. القضاء على استعلامات N+1 في فحص الأعطال المانعة

> 💡 **الشرح الفني للأداء:** عند عرض قائمة بـ 200 غرفة، إذا قمنا بفحص وجود عطل مانع لكل غرفة عبر دالة منفصلة في الـ Serializer، فسيتم إرسال 200 استعلام إضافي لقاعدة البيانات!
> **الحل الهندسي:** استخدام `Exists` Subquery Annotation داخل الاستعلام الأصلي للغرف، فيتم حساب الحالة مباشرة في استعلام واحد فقط!

### The Problem

A common implementation mistake when building a room list view with a `has_blocking_issue` field is to use a `SerializerMethodField`:

```python
# ❌ Anti-pattern: causes N+1 queries
class RoomSerializer(serializers.ModelSerializer):
    has_blocking_issue = serializers.SerializerMethodField()

    def get_has_blocking_issue(self, obj):
        return RoomIssue.objects.filter(
            room=obj,
            blocking=True,
            status__in=[IssueStatus.OPEN, IssueStatus.IN_PROGRESS],
        ).exists()
```

With this approach, Django executes **one additional SQL query per room** in the list. For a hotel with 200 rooms, a single list request fires 201 queries (1 for rooms + 200 for issue checks).

### The Solution: `Exists` Subquery Annotation

The correct approach annotates the queryset **once** with a correlated `Exists` subquery. The database evaluates the existence check for all rooms in a single SQL statement:

```python
from django.db.models import Exists, OuterRef

def get_rooms_with_blocking_flag(hotel):
    blocking_issue = RoomIssue.objects.filter(
        room=OuterRef('pk'),
        blocking=True,
        status__in=[IssueStatus.OPEN, IssueStatus.IN_PROGRESS],
    )
    return Room.objects.filter(hotel=hotel).annotate(
        has_blocking_issue=Exists(blocking_issue)
    ).select_related('room_type')
```

The serializer then reads the pre-computed annotation directly from the instance — no additional queries are executed:

```python
class RoomSerializer(serializers.ModelSerializer):
    has_blocking_issue = serializers.BooleanField(read_only=True)
```

### Query Count Comparison

| Approach | Queries for 200 Rooms |
|---|---|
| `SerializerMethodField` (anti-pattern) | 201 |
| `Exists` annotation (correct) | 1 |

The annotation approach scales to any number of rooms with a constant query count. This is enforced by a dedicated `assertNumQueries(1, ...)` test. See [Section 12](#12-tests-summary).

---

## 8. Complaints Lifecycle | ٨. دورة حياة ومتابعة شكاوى النزلاء

> 💡 **شرح دورة الشكوى:** تبدأ مفتوحة (`open`)، ثم تُعين لموظف فتصبح جارية (`in_progress`)، وعند المعالجة تُسجل ملاحظات الحل وتتحول إلى تم الحل (`resolved`) ثم إغلاق نهائي (`closed`).

### Status Transitions

```
OPEN
  │
  │  staff member assigned (assigned_to set)
  ▼
IN_PROGRESS
  │
  │  resolution_notes filled, resolved_at set
  ▼
RESOLVED  ◄── Terminal State (cannot be reopened)
```

### Transition Rules

| Transition | Required Fields | Side Effects |
|---|---|---|
| `OPEN → IN_PROGRESS` | `assigned_to` must be set | No timestamp changes at this step |
| `IN_PROGRESS → RESOLVED` | `resolution_notes` must be non-empty | `resolved_at` set to `timezone.now()` |

### Terminal State

`RESOLVED` is a **terminal state**. Once a complaint is resolved, it cannot be transitioned back to `IN_PROGRESS` or `OPEN`. If a customer raises the same issue again, a new `CustomerComplaint` record must be created. This design preserves the integrity of the audit trail — each complaint represents a discrete, independent incident.

### Priority Levels

| Priority | Intended Use |
|---|---|
| `LOW` | Minor inconvenience; no immediate operational impact |
| `MEDIUM` | Noticeable guest dissatisfaction; requires attention within the shift |
| `HIGH` | Serious guest dissatisfaction or potential reputational/legal risk; immediate escalation required |

### Reservation Linkage

The optional `reservation` foreign key on `CustomerComplaint` allows front-desk staff and complaint handlers to immediately access the guest's check-in/check-out dates, room assignment, and payment history when investigating a complaint. It is nullable to support complaints raised outside of an active or recent reservation (e.g., a walk-in customer who was turned away).

---

## 9. Celery Tasks | ٩. مهام الخلفية وإعادة المحاولة الذكية (Celery Tasks)

> 💡 **شرح مهمة الإشعار:** مهمة `notify_high_priority_issue` مجهزة بإعادة المحاولة الذكية حتى 3 مرات مع تدرج زمني في حال تعذر إرسال الإشعار، لضمان عدم ضياع بلاغات الطوارئ.

### `notify_high_priority_issue`

**Module:** `maintenance/tasks.py`

**Purpose:** Retrieves the `RoomIssue` identified by `issue_id` and dispatches notifications to hotel management via email and an in-app notification placeholder.

**Signature:**

```python
@shared_task(bind=True, max_retries=3)
def notify_high_priority_issue(self, issue_id):
    try:
        issue = RoomIssue.objects.select_related('hotel', 'room', 'reported_by').get(id=issue_id)
        # Send email notification to hotel management
        send_mail(
            subject=f"[{issue.priority}] Maintenance Issue: {issue.title}",
            message=f"Room {issue.room.room_number} — {issue.description}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=get_hotel_management_emails(issue.hotel),
        )
        # In-app notification placeholder
        # InAppNotification.objects.create(hotel=issue.hotel, ...)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**Configuration:**

| Parameter | Value | Explanation |
|---|---|---|
| `bind=True` | — | Gives the task access to `self` for retry control |
| `max_retries` | `3` | The task will be attempted a maximum of 4 times (1 initial + 3 retries) before failing permanently |
| `countdown` | `60 * (2 ** self.request.retries)` | Exponential backoff: 60s, 120s, 240s between retries |

**Retry Backoff Schedule:**

| Attempt | Delay Before Retry |
|---|---|
| 1st retry | 60 seconds |
| 2nd retry | 120 seconds |
| 3rd retry | 240 seconds |
| After 3rd failure | Task moves to dead-letter queue |

**Observability:** Failed tasks and retry attempts are visible in Flower and structured application logs. The Celery result backend stores the final state (`SUCCESS` / `FAILURE`) for each task execution.

---

## 10. API Endpoints | ١٠. نقاط النهاية للواجهات التشغيلية (REST Endpoints)

> 💡 **شرح الـ Endpoints:** توثيق كامل لكافة مسارات الـ API للإشراف الداخلي والصيانة والشكاوى، متضمنة مسارات الإجراءات الخاصة مثل `/action/`, `/resolve/`, `/assign/`.

### Housekeeping

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/housekeeping/cleanings/` | List all cleaning tasks for the hotel | JWT + `housekeeping.view` |
| `POST` | `/api/v1/housekeeping/cleanings/` | Create a new cleaning task manually | JWT + `housekeeping.manage` |
| `PATCH` | `/api/v1/housekeeping/cleanings/{id}/` | Update cleaning task fields (e.g., notes) | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/assign/` | Assign a housekeeper to the task | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/start/` | Transition task to `IN_PROGRESS` | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/complete/` | Transition task to `COMPLETED` | JWT + `housekeeping.manage` |
| `POST` | `/api/v1/housekeeping/cleanings/{id}/inspect/` | Transition task to `INSPECTED`; triggers `mark_available()` | JWT + `housekeeping.manage` |

### Maintenance

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/maintenance/issues/` | List all maintenance issues for the hotel | JWT + `maintenance.view` |
| `POST` | `/api/v1/maintenance/issues/` | Report a new maintenance issue | JWT + `maintenance.manage` |
| `GET` | `/api/v1/maintenance/issues/{id}/` | Retrieve full detail of a specific issue | JWT + `maintenance.view` |
| `PATCH` | `/api/v1/maintenance/issues/{id}/` | Update issue fields (assign, change priority, etc.) | JWT + `maintenance.manage` |
| `POST` | `/api/v1/maintenance/issues/{id}/resolve/` | Resolve the issue; set `resolved_at` and `resolution_notes` | JWT + `maintenance.manage` |

### Complaints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/complaints/` | List all complaints for the hotel | JWT + `complaints.view` |
| `POST` | `/api/v1/complaints/` | Submit a new customer complaint | JWT + `complaints.manage` |
| `GET` | `/api/v1/complaints/{id}/` | Retrieve full detail of a specific complaint | JWT + `complaints.view` |
| `PATCH` | `/api/v1/complaints/{id}/` | Update complaint fields | JWT + `complaints.manage` |
| `POST` | `/api/v1/complaints/{id}/assign/` | Assign a staff member to handle the complaint | JWT + `complaints.manage` |
| `POST` | `/api/v1/complaints/{id}/resolve/` | Resolve the complaint; terminal state | JWT + `complaints.manage` |

---

## 11. Permissions | ١١. مصفوفة الصلاحيات التشغيلية (RBAC)

> 💡 **شرح الصلاحيات:** فصل دقيق لصلاحيات العرض والإدارة للأقسام التشغيلية الثلاثة: `housekeeping`, `maintenance`, `complaints`.

All Phase 7 endpoints use the JWT authentication established in Phase 3. Access is gated by fine-grained permission codes that are assigned to staff roles within each hotel's tenant context.

| Permission Code | Scope | Grants |
|---|---|---|
| `housekeeping.view` | Housekeeping | Read-only access to cleaning tasks (`GET` endpoints) |
| `housekeeping.manage` | Housekeeping | Full CRUD plus all action endpoints: assign, start, complete, inspect |
| `maintenance.view` | Maintenance | Read-only access to maintenance issues (`GET` endpoints) |
| `maintenance.manage` | Maintenance | Create, update, and resolve maintenance issues |
| `complaints.view` | Complaints | Read-only access to complaints (`GET` endpoints) |
| `complaints.manage` | Complaints | Create, update, assign, and resolve complaints |

**Multi-tenant isolation:** All list views filter by `hotel`, which is extracted from the authenticated user's active hotel context. A user from Hotel A cannot access the cleaning tasks, issues, or complaints of Hotel B, regardless of their permission codes.

---

## 12. Tests Summary | ١٢. ملخص نتائج الاختبارات الآلية (18 اختباراً ناجحاً)

> 💡 **ملخص الاختبارات:** 18 اختباراً شاملاً يغطي دورات عمل التنظيف، حظر الأعطال، فك الحظر بعد الإصلاح، إطلاق إشارات Celery، وإجراءات حل الشكاوى.

**Total: 18 tests** across three test modules.

### `tests/test_housekeeping.py` — 8 Tests

| # | Test Description | Type |
|---|---|---|
| 1 | `_check_no_blocking_issues()` raises `RoomBlockedError` when a blocking `RoomIssue` is `OPEN` | Unit |
| 2 | `_check_no_blocking_issues()` raises `RoomBlockedError` when a blocking `RoomIssue` is `IN_PROGRESS` | Unit |
| 3 | `_check_no_blocking_issues()` does not raise when the blocking issue is `RESOLVED` | Unit |
| 4 | `_create_cleaning_tasks()` creates one `RoomCleaning` record per active reservation room | Unit |
| 5 | `_create_cleaning_tasks()` skips soft-deleted reservation rooms (`is_deleted=True`) | Unit |
| 6 | Valid housekeeping status transition `PENDING → IN_PROGRESS` succeeds and sets `started_at` | Unit |
| 7 | Valid transition `IN_PROGRESS → COMPLETED` succeeds and sets `completed_at` | Unit |
| 8 | Valid transition `COMPLETED → INSPECTED` succeeds and sets `inspected_at` | Unit |

### `tests/test_maintenance.py` — 6 Tests

| # | Test Description | Type |
|---|---|---|
| 9 | `inspect_cleaning()` calls `RoomService.mark_available()`; room becomes `AVAILABLE` when no blocking issues exist | Integration |
| 10 | `inspect_cleaning()` catches `RoomBlockedError`; room status is set to `MAINTENANCE` | Integration |
| 11 | Creating a `RoomIssue` with `priority=HIGH` dispatches `notify_high_priority_issue` Celery task | Unit |
| 12 | Creating a `RoomIssue` with `priority=CRITICAL` dispatches `notify_high_priority_issue` Celery task | Unit |
| 13 | Creating a `RoomIssue` with `priority=LOW` does **not** dispatch the Celery task | Unit |
| 14 | N+1 query count: room list with blocking annotation executes exactly **1 query** (`assertNumQueries(1, ...)`) | Performance |

### `tests/test_complaints.py` — 4 Tests

| # | Test Description | Type |
|---|---|---|
| 15 | Complaint lifecycle `OPEN → IN_PROGRESS`: `assigned_to` is set correctly | Unit |
| 16 | Complaint lifecycle `IN_PROGRESS → RESOLVED`: `resolution_notes` saved and `resolved_at` set | Unit |
| 17 | Attempting to transition a `RESOLVED` complaint raises `InvalidTransitionError` (terminal state) | Unit |
| 18 | `notify_high_priority_issue` task retries with exponential backoff on `Exception` | Unit |

---

## 13. Files Changed | ١٣. جدول الملفات المنشأة والمعدلة

> 💡 **دليل الملفات:** يشمل ملفات التطبيقات الثلاثة الجديدة وتحديثات ملفات المراحل السابقة التي تم استكمال ربطها.

### New Applications

#### `housekeeping/`

| File | Action | What Changed |
|---|---|---|
| `housekeeping/models.py` | **CREATED** | `RoomCleaning` model with `CleaningStatus` choices and all timestamp fields |
| `housekeeping/services.py` | **CREATED** | `HousekeepingService` with `assign_housekeeper()`, `start_cleaning()`, `complete_cleaning()`, `inspect_cleaning()` |
| `housekeeping/selectors.py` | **CREATED** | `get_cleaning_tasks()` selector with `select_related` and `prefetch_related` to avoid N+1 in list views |
| `housekeeping/serializers.py` | **CREATED** | `RoomCleaningSerializer` and `RoomCleaningDetailSerializer` |
| `housekeeping/views.py` | **CREATED** | `HousekeepingViewSet` with `@action` decorators for `assign`, `start`, `complete`, `inspect` |
| `housekeeping/urls.py` | **CREATED** | Router registration for `/api/v1/housekeeping/` |

#### `maintenance/`

| File | Action | What Changed |
|---|---|---|
| `maintenance/models.py` | **CREATED** | `RoomIssue` model with `IssuePriority`, `IssueStatus` choices, `blocking` flag, and `db_index=True` on `priority` |
| `maintenance/signals.py` | **CREATED** | `post_save` receiver on `RoomIssue` dispatching `notify_high_priority_issue` for `HIGH` / `CRITICAL` issues |
| `maintenance/tasks.py` | **CREATED** | `notify_high_priority_issue` Celery task with `max_retries=3` and exponential backoff |
| `maintenance/services.py` | **CREATED** | `MaintenanceService` with `assign_issue()`, `start_issue()`, `resolve_issue()`, `close_issue()` |
| `maintenance/selectors.py` | **CREATED** | `get_rooms_with_blocking_flag()` using `Exists` subquery annotation |
| `maintenance/serializers.py` | **CREATED** | `RoomIssueSerializer` and `RoomIssueDetailSerializer` |
| `maintenance/views.py` | **CREATED** | `MaintenanceViewSet` with `@action` decorator for `resolve` |
| `maintenance/urls.py` | **CREATED** | Router registration for `/api/v1/maintenance/` |

#### `complaints/`

| File | Action | What Changed |
|---|---|---|
| `complaints/models.py` | **CREATED** | `CustomerComplaint` model with `ComplaintPriority`, `ComplaintStatus` choices and optional `reservation` FK |
| `complaints/services.py` | **CREATED** | `ComplaintService` with `assign_complaint()`, `resolve_complaint()` and terminal-state enforcement |
| `complaints/serializers.py` | **CREATED** | `CustomerComplaintSerializer` and `CustomerComplaintDetailSerializer` |
| `complaints/views.py` | **CREATED** | `ComplaintViewSet` with `@action` decorators for `assign`, `resolve` |
| `complaints/urls.py` | **CREATED** | Router registration for `/api/v1/complaints/` |

### Modified Existing Files

| File | Action | What Changed |
|---|---|---|
| `rooms/services.py` | **MODIFIED** | `_check_no_blocking_issues()` fully implemented — replaces Phase 4 placeholder that always returned `True` |
| `reservations/services.py` | **MODIFIED** | `_create_cleaning_tasks()` fully implemented — replaces Phase 5 placeholder with `pass` body |

### Test Files

| File | Action | What Changed |
|---|---|---|
| `tests/test_housekeeping.py` | **CREATED** | 8 tests covering `_check_no_blocking_issues`, `_create_cleaning_tasks`, status transitions, and inspection integration |
| `tests/test_maintenance.py` | **CREATED** | 6 tests covering blocking logic, Celery task dispatch, and N+1 query count |
| `tests/test_complaints.py` | **CREATED** | 4 tests covering full complaint lifecycle and terminal state enforcement |

---

## 14. Migrations | ١٤. ترحيلات قاعدة البيانات للمرحلة السابعة

> 💡 **شرح المايجريشن:** يوثق إنشاء جداول `housekeeping_roomcleaning`، `maintenance_roomissue`، و `complaints_customercomplaint` مع كافة الفهارس والقيود.

Three new migration files are created in this phase — one per new application. All use the standard Django `migrations.CreateModel` operation.

### `housekeeping/migrations/0001_initial.py`

**Creates:** `housekeeping_roomcleaning` table

**Key schema details:**
- UUID primary key with `default=uuid.uuid4`
- Foreign keys to `hotels_hotel`, `rooms_room`, `reservations_reservation` (nullable), `users_user` (nullable for `assigned_to`)
- `status` VARCHAR with `CleaningStatus` choices; default `PENDING`
- Nullable `DateTimeField` columns for `started_at`, `completed_at`, `inspected_at`

### `maintenance/migrations/0001_initial.py`

**Creates:** `maintenance_roomissue` table

**Key schema details:**
- UUID primary key with `default=uuid.uuid4`
- Foreign keys to `hotels_hotel`, `rooms_room`, `users_user` (for `reported_by` and nullable `assigned_to`)
- `priority` VARCHAR with `IssuePriority` choices; `db_index=True` → explicit B-tree index on `priority` column
- `blocking` BOOLEAN with `default=False`
- `status` VARCHAR with `IssueStatus` choices; default `OPEN`
- Nullable `resolved_at` DateTimeField

### `complaints/migrations/0001_initial.py`

**Creates:** `complaints_customercomplaint` table

**Key schema details:**
- UUID primary key with `default=uuid.uuid4`
- Foreign keys to `hotels_hotel`, `users_user` (for `customer` and nullable `assigned_to`), `reservations_reservation` (nullable)
- `priority` VARCHAR with `ComplaintPriority` choices
- `status` VARCHAR with `ComplaintStatus` choices; default `OPEN`
- Nullable `resolved_at` DateTimeField

---

*End of Phase 7 Documentation*
