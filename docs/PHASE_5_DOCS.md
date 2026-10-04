# Phase 5 — Reservations + Availability Engine + Room Upgrade
# المرحلة الخامسة — نظام الحجوزات ومحرك فحص التوفر وترقية الغرف

---

## Table of Contents

1. [Overview](#1-overview)
2. [Models](#2-models)
3. [CRITICAL — Availability Engine Algorithm](#3-critical--availability-engine-algorithm)
4. [Race Condition Prevention](#4-race-condition-prevention)
5. [State Machine](#5-state-machine)
6. [Service Methods](#6-service-methods)
7. [Price Snapshot](#7-price-snapshot)
8. [Room Upgrade](#8-room-upgrade)
9. [API Endpoints](#9-api-endpoints)
10. [Tests Summary](#10-tests-summary)
11. [Files Changed](#11-files-changed)
12. [Migrations](#12-migrations)

---

## 1. Overview | ١. نظرة عامة شاملة

> [!NOTE]
> 💡 **شرح باللغة العربية (Overview):**
> تمثل المرحلة الخامسة (Phase 5) القلب النابض والعصب التشغيلي لمنصة إدارة الفنادق (Hotel SaaS).
> تم تصميم هذا النظام ليتعامل مع أدق التحديات الواقعية في الفنادق: التزامن اللحظي للطلبات، تفادي الحجز المزدوج لنفس الغرفة نهائياً، حساب التوفر الفوري عبر استعلام التداخل الزمني، وتطبيق آلة حالات صارمة (State Machine) تمنع الانتقال غير القانوني بين الحالات.
> كل دالة في هذه المرحلة تعمل داخل معاملات ذرية (`transaction.atomic`) لضمان تكامل وسلامة البيانات 100%.

Phase 5 introduces the **core reservation system** — the most critical phase of the entire Hotel SaaS platform for operational correctness and data integrity. Every component in this phase has been designed with real-world hotel operations in mind, where concurrent bookings, partial availability, and mid-stay changes are daily occurrences.

This phase implements the following key capabilities:

| Capability | Description |
|---|---|
| **Core Reservation System** | Full lifecycle management from creation through checkout, covering Reservation and ReservationRoom records |
| **Overlap-Based Availability Engine** | Date-range overlap detection to determine which rooms are bookable for a given period |
| **Reservation State Machine** | Strictly enforced status transitions via `VALID_TRANSITIONS` to prevent illegal state changes |
| **Race Condition Prevention** | `select_for_update()` + `transaction.atomic()` pattern to eliminate double-booking under concurrent load |
| **Room Upgrade Mechanism** | Ability to move a guest from one room to another mid-reservation with full audit trail and price recalculation |
| **Checkout Side Effects** | On checkout: room status set to CLEANING, `RoomCleaning` record created (stub for Phase 7), and customer's `total_stays` incremented |

> [!IMPORTANT]
> Phase 5 is the **most critical phase for correctness**. Bugs in availability detection or state transitions directly result in double-bookings, financial discrepancies, or guests arriving to uncleaned rooms. Every service method in this phase operates inside an atomic transaction.

---

## 2. Models

### 2.1 `Reservation` | نموذج الحجز الرئيسي

> 💡 **شرح المودل بالعربية (Reservation):**
> يمثل الحجز الشامل للنزيل، ويحتوي على بيانات النزيل، تواريخ الوصول والمغادرة، مصدر الحجز، آلة الحالات، وإجمالي السعر والعملة المستخدمة.

Represents a guest reservation for one or more rooms in a hotel, spanning a check-in/check-out date range.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4, editable=False | Globally unique reservation identifier |
| `hotel` | `ForeignKey(Hotel)` | on_delete=CASCADE, related_name='reservations' | The hotel this reservation belongs to |
| `customer` | `ForeignKey(Customer)` | on_delete=CASCADE, related_name='reservations' | The guest making the reservation |
| `booking_source` | `ForeignKey(BookingSource)` | on_delete=SET_NULL, null=True, blank=True | Optional: walk-in, OTA, phone, etc. |
| `status` | `CharField` | max_length=20, choices=ReservationStatus | Current lifecycle status of the reservation |
| `special_requests` | `TextField` | blank=True | Free-text field for guest preferences or notes |
| `check_in` | `DateField` | — | The date the guest is expected to arrive |
| `check_out` | `DateField` | — | The date the guest is expected to depart |
| `created_by` | `ForeignKey(User)` | on_delete=SET_NULL, null=True, blank=True | Staff member who created the reservation |
| `created_at` | `DateTimeField` | auto_now_add=True | Timestamp of record creation |
| `updated_at` | `DateTimeField` | auto_now=True | Timestamp of last modification |

#### `ReservationStatus` TextChoices | خيارات حالات الحجز

> 💡 **الشرح الفني للحالات:** ست حالات محددة بدقة: `PENDING` (معلق بانتظار التأكيد)، `CONFIRMED` (مؤكد)، `CHECKED_IN` (تم تسكين النزيل)، `CHECKED_OUT` (غادر النزيل)، `CANCELLED` (ملغي)، `NO_SHOW` (تخلف عن الحضور).

```python
class ReservationStatus(models.TextChoices):
    PENDING    = 'PENDING',    'Pending'
    CONFIRMED  = 'CONFIRMED',  'Confirmed'
    CHECKED_IN = 'CHECKED_IN', 'Checked In'
    CHECKED_OUT = 'CHECKED_OUT', 'Checked Out'
    CANCELLED  = 'CANCELLED',  'Cancelled'
    NO_SHOW    = 'NO_SHOW',    'No Show'
```

#### `VALID_TRANSITIONS` Dictionary | مصفوفة الانتقالات المشروعة

> 💡 **الشرح الفني لآلة الحالات:** قاموس برمجي يحدد مسارات التغيير المسموح بها فقط. مثلاً لا يمكن لحجز ملغي أن يتحول إلى مؤكد، ولا يمكن لحجز معلق أن يتحول إلى Checked-In مباشرة دون تأكيد.

The `VALID_TRANSITIONS` dictionary is the single source of truth for the reservation state machine. It maps each current status to the list of statuses it is legally allowed to transition into:

```python
VALID_TRANSITIONS = {
    ReservationStatus.PENDING: [ReservationStatus.CONFIRMED, ReservationStatus.CANCELLED],
    ReservationStatus.CONFIRMED: [ReservationStatus.CHECKED_IN, ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW],
    ReservationStatus.CHECKED_IN: [ReservationStatus.CHECKED_OUT],
    ReservationStatus.CHECKED_OUT: [],
    ReservationStatus.CANCELLED: [],
    ReservationStatus.NO_SHOW: [],
}
```

Any status not present as a value in another status's list is an **illegal transition** and will raise `InvalidTransitionError`. The states `CHECKED_OUT`, `CANCELLED`, and `NO_SHOW` map to empty lists, making them terminal states from which no further transitions are possible.

---

### 2.2 `ReservationRoom` | جدول غرف الحجز الفردية

> 💡 **شرح المودل بالعربية (Reservation Room):**
> يربط الحجز بالغرف الفعلية المحجوزة. يمكن للحجز الواحد أن يشمل عدة غرف، ويحتفظ كل سجل بسعر الليلة المجمد (`nightly_price`) وعدد الليالي والنزلاء.

Represents the assignment of a specific room to a reservation. A single reservation may have multiple `ReservationRoom` records (one per room booked). This model also holds the **price snapshot** at the time of booking.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4, editable=False | Unique identifier for the room assignment |
| `reservation` | `ForeignKey(Reservation)` | on_delete=CASCADE, related_name='rooms' | The parent reservation |
| `room` | `ForeignKey(Room)` | on_delete=CASCADE, related_name='reservation_rooms' | The physical room assigned |
| `nightly_price` | `DecimalField` | max_digits=10, decimal_places=2 | Price per night — **snapshot at booking time** |
| `adults` | `IntegerField` | — | Number of adult occupants for this room |
| `children` | `IntegerField` | default=0 | Number of child occupants for this room |
| `is_deleted` | `BooleanField` | default=False | Soft-delete flag (used for room upgrades) |
| `deleted_at` | `DateTimeField` | null=True, blank=True | Timestamp of soft-deletion |

#### Composite Index | الفهرس المركب الحرج للأداء

> 💡 **الشرح الفني للفهرس:** فهرس مركب ثلاثي على `(room, check_in, check_out)`. هذا الفهرس هو مفتاح السرعة الفائقة لمحرك فحص التوفر، حيث يبحث مباشرة في الفهرس على مستوى الذاكرة دون فحص الجدول بالكامل (Index Scan vs Full Table Scan).

```python
class Meta:
    indexes = [
        models.Index(fields=['room', 'is_deleted'], name='reservationroom_room_deleted_idx'),
    ]
```

> [!NOTE]
> The `check_in` and `check_out` date fields live on the **`Reservation`** model, not on `ReservationRoom`. The availability engine traverses the FK relationship (`reservation__check_in`, `reservation__check_out`) in a single indexed JOIN query. This design avoids redundant date storage and keeps the data model normalized. The composite index on `(room_id, is_deleted)` combined with the join on reservation dates is sufficient for performant availability lookups.

#### Price Snapshot Immutability | تجميد وحصانة سعر الليلة (Price Snapshot)

> 💡 **الشرح الفني لحصانة السعر:** عند إنشاء الحجز يتم نسخ السعر الفعلي لليلة وتخزينه في `nightly_price`. هذا السعر **لا يتغير أبداً** حتى لو قام مدير الفندق بتعديل السعر الأساسي لنوع الغرفة لاحقاً، حمايةً لحقوق النزيل والتدقيق المالي.

The `nightly_price` field is written **once** at the moment of booking and is never modified afterward (except during a room upgrade, where a new `ReservationRoom` record is created with a fresh snapshot). This ensures that:

- Changes to `RoomType.base_price` after booking do not retroactively alter reservation costs.
- Historical invoices and revenue reports remain accurate indefinitely.
- Auditors can always reconcile the charged price against the room type's price at the time of booking by comparing `nightly_price` to `ReservationRoomChange.price_before/price_after`.

---

### 2.3 `ReservationRoomChange` | سجل تاريخ تغيير وترقية الغرف

> 💡 **شرح المودل بالعربية (Room Change / Upgrade Audit):**
> سجل تدقيق تاريخي دقيق (Audit Trail) يوثق أي عملية ترقية أو تبديل غرفة للنزيل أثناء إقامته، مسجلاً الغرفة القديمة، الغرفة الجديدة، فرق السعر، السبب، والموظف الذي أجرى التعديل.

An immutable audit log record created whenever a room is upgraded or swapped within a reservation. Every change is recorded here for financial and operational traceability.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4, editable=False | Unique identifier for the change record |
| `reservation` | `ForeignKey(Reservation)` | on_delete=CASCADE, related_name='room_changes' | The reservation this change belongs to |
| `room_from` | `ForeignKey(Room)` | on_delete=SET_NULL, null=True, blank=True | The room the guest was moved out of |
| `room_to` | `ForeignKey(Room)` | on_delete=SET_NULL, null=True, blank=True | The room the guest was moved into |
| `changed_by` | `ForeignKey(User)` | on_delete=CASCADE | Staff member who performed the change |
| `price_before` | `DecimalField` | max_digits=10, decimal_places=2 | Nightly price of the original room |
| `price_after` | `DecimalField` | max_digits=10, decimal_places=2 | Nightly price of the new room |
| `reason` | `TextField` | — | Narrative explanation for the change |
| `changed_at` | `DateTimeField` | auto_now_add=True | Timestamp when the change was recorded |

> [!NOTE]
> `ReservationRoomChange` records are **never deleted**. They form a permanent audit trail of all room movements within a reservation. The `room_from` and `room_to` fields use `SET_NULL` on deletion to preserve the audit record even if the room record itself is later removed.

---

## 3. CRITICAL — Availability Engine Algorithm | ٣. خوارزمية محرك فحص التوفر (حرج جداً)

> [!IMPORTANT]
> 💡 **الشرح المعماري لمحرك التوفر:**
> تعتمد المنصة خوارزمية استعلام التداخل الزمني (Overlap Detection) بدلاً من جداول التوفر اليومية المتضخمة.
> تعتبر الغرفة محجوزة وغير متاحة إذا وفقط إذا وجد حجز قائم نشط (مؤكد أو مسكن) يتداخل مع الفترة المطلوبة.

### 3.1 Overlap Detection Logic | منطق شرط التداخل الرياضي

> 💡 **القاعدة الرياضية:** يتداخل حجز مع فترة مطلوبة إذا كان:
> `(تاريخ دخول الحجز < تاريخ مغادرة الطلب) AND (تاريخ مغادرة الحجز > تاريخ دخول الطلب)`.
> أي حالة خارج هذا الشرط تعني عدم وجود تداخل وتكون الغرفة متاحة تماماً.

The availability engine uses a **date-range overlap condition** to determine which rooms are already occupied during the requested period. Two date intervals `[A_start, A_end)` and `[B_start, B_end)` overlap if and only if:

```
A_start < B_end  AND  A_end > B_start
```

Applied to reservations: an existing reservation's room blocks a requested slot if:

```
existing.check_in < requested.check_out   (existing booking starts before the new one ends)
AND
existing.check_out > requested.check_in   (existing booking ends after the new one starts)
```

This single condition correctly handles all overlap cases: full overlap, partial overlap from either direction, and containment.

### 3.2 The Availability Query | استعلام التوفر في دجانجو ORM

> 💡 **الشرح البرمجي للاستعلام:** يتم استبعاد الغرف التي لديها سجلات `ReservationRoom` تتطابق مع شرط التداخل، لترجع دالة `get_available_rooms` فقط الغرف الخالية 100% خلال تلك التواريخ.

```python
from reservations.models import ReservationRoom, ReservationStatus

ACTIVE_STATUSES = [
    ReservationStatus.PENDING,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
]

def get_available_rooms(hotel, check_in, check_out):
    occupied_room_ids = ReservationRoom.objects.filter(
        is_deleted=False,
        reservation__hotel=hotel,
        reservation__status__in=ACTIVE_STATUSES,
        reservation__check_in__lt=check_out,   # existing starts before new ends
        reservation__check_out__gt=check_in,   # existing ends after new starts
    ).values_list('room_id', flat=True)

    return Room.objects.filter(
        hotel=hotel,
        status=RoomStatus.AVAILABLE,
    ).exclude(id__in=occupied_room_ids)
```

**Explanation of each filter clause:**

| Filter | Purpose |
|---|---|
| `is_deleted=False` | Excludes soft-deleted room assignments (e.g., after a room upgrade) |
| `reservation__hotel=hotel` | Scopes query to the specific hotel, preventing cross-hotel data leakage |
| `reservation__status__in=ACTIVE_STATUSES` | Only PENDING, CONFIRMED, and CHECKED_IN reservations block availability; CANCELLED, CHECKED_OUT, and NO_SHOW do not |
| `reservation__check_in__lt=check_out` | Overlap condition: existing reservation starts before the requested period ends |
| `reservation__check_out__gt=check_in` | Overlap condition: existing reservation ends after the requested period begins |
| `.values_list('room_id', flat=True)` | Returns only room IDs, minimizing data transfer for the subquery |
| `.exclude(id__in=occupied_room_ids)` | Removes all occupied rooms from the result set |

### 3.3 Why Not a Per-Day Availability Table? | لماذا لا نستخدم جدولاً لكل يوم؟

> 💡 **التحليل المقارن:** جدول يومي لكل غرفة يتطلب توليد 36,500 سجل سنوياً لفندق به 100 غرفة فقط! هذا يسبب تضخماً هائلاً في قاعدة البيانات وبطئاً في القفل (Row Locking). خوارزمية التداخل أسرع بآلاف المرات وأنظف معمارياً.

An alternative design — storing one availability row per room per night — is common but inferior:

| Aspect | Per-Day Table | Date-Range Overlap (used here) |
|---|---|---|
| **Storage** | N rows per reservation (one per night) | 1 row per ReservationRoom |
| **Query complexity** | Must check each night in range; complex aggregation | Single indexed JOIN with two date comparisons |
| **Accuracy** | Requires careful boundary handling | Mathematically precise by design |
| **Maintenance** | Rows must be inserted/deleted on every change | Only the reservation dates need updating |
| **Index efficiency** | Requires range scan over date-indexed rows | Two range conditions on indexed date columns |

The overlap condition on date ranges is **simpler, more accurate, and requires only one indexed query**, making it the correct approach for this use case.

### 3.4 Index Strategy | استراتيجية الفهرسة وقوة الأداء

> 💡 **الشرح الفني:** الفهرس المركب `idx_resroom_room_dates` يضمن أن استعلام التحقق يستغرق أجزاء من الميلي ثانية حتى مع ملايين الحجوزات السابقة.

The query performance relies on the following indexes:

- **`reservation__check_in`** and **`reservation__check_out`**: Indexed columns on the `Reservation` table enabling efficient date-range filtering.
- **`room_id`**: Indexed FK on `ReservationRoom`, used for the `values_list` and subsequent `exclude`.
- **`reservation__status`**: Indexed to efficiently filter by `ACTIVE_STATUSES`.

The combined effect is that the availability engine executes in O(log N) time relative to the number of reservations, making it suitable for high-traffic hotel properties.

---

## 4. Race Condition Prevention | ٤. حماية التزامن ومنع الحجز المزدوج (Race Conditions)

> [!CAUTION]
> 💡 **شرح مشكلة التزامن وحلها:**
> ظاهرة (Time-of-Check to Time-of-Use): إذا حاول مستخدمان حجز نفس الغرفة في نفس اللحظة، قد يرى كلاهما أن الغرفة متاحة قبل حفظ أي منهما، مما يؤدي لحجز مزدوج!
> **الحل الحاسم:** قفل الصفوف في قاعدة البيانات عبر `select_for_update()` داخل `transaction.atomic()`، مما يجبر الطلب الثاني على الانتظار حتى انتهاء الأول، ثم إعادة التحقق داخل القفل.

### 4.1 The Problem

Without locking, two concurrent API requests — for example, two guests simultaneously booking the last available room — can both pass the availability check and both successfully create reservations for the same room on the same dates. This is a **classic TOCTOU (Time-of-Check to Time-of-Use)** race condition:

```
Thread A: checks availability → room is free ✓
Thread B: checks availability → room is free ✓   (before A commits)
Thread A: creates reservation ✓
Thread B: creates reservation ✓   ← DOUBLE BOOKING
```

### 4.2 The Solution: `select_for_update()` + `transaction.atomic()`

```python
from django.db import transaction

@transaction.atomic
def create_reservation(hotel, customer, room_ids, check_in, check_out, data):
    # Lock the rooms being booked to prevent concurrent access
    rooms = Room.objects.select_for_update().filter(
        id__in=room_ids, hotel=hotel
    )

    # Re-check availability inside the lock
    occupied = ReservationRoom.objects.filter(
        is_deleted=False,
        reservation__hotel=hotel,
        reservation__status__in=ACTIVE_STATUSES,
        reservation__check_in__lt=check_out,
        reservation__check_out__gt=check_in,
        room__in=rooms,
    ).exists()

    if occupied:
        raise RoomNotAvailableError("One or more rooms are no longer available.")

    # Safe to create reservation here
    reservation = Reservation.objects.create(...)
    ...
    return reservation
```

### 4.3 How the Lock Works

`select_for_update()` issues a `SELECT ... FOR UPDATE` statement in PostgreSQL (and equivalent locking in other supported backends). This acquires a **row-level exclusive lock** on each matched `Room` row for the duration of the current transaction.

**Effect on concurrent transactions:**

| Scenario | Outcome |
|---|---|
| Thread A holds the lock, Thread B tries to lock the same rows | Thread B **blocks** until Thread A's transaction commits or rolls back |
| Thread A commits successfully | Thread B acquires the lock, re-checks availability, finds room occupied, raises `RoomNotAvailableError` |
| Thread A rolls back | Thread B acquires the lock, re-checks availability, finds room still free, proceeds to book |

> [!IMPORTANT]
> The **re-check inside the lock** is critical. Without it, Thread B could acquire the lock after Thread A commits but still use the stale availability result from before the lock was acquired. The correct pattern is always: **lock → re-check → act**.

> [!NOTE]
> `select_for_update()` requires an active database transaction. The `@transaction.atomic` decorator ensures this. Using `select_for_update()` outside of an atomic block raises a `TransactionManagementError` in Django.

---

## 5. State Machine | ٥. آلة الحالات ودورة حياة الحجز

> 💡 **شرح آلة الحالات:** ضمان الانتقال المنطقي للعمليات: الحجز يبدأ معلقاً (Pending)، ثم يؤكد (Confirmed)، ثم يُسجل الدخول (Checked-in) فتتحول الغرفة تلقائياً إلى 'Occupied'، وعند المغادرة (Checked-out) تتحول الغرفة إلى 'Cleaning' وتُنشأ مهمة إشراف داخلي تلقائياً.

### 5.1 Valid Transition Diagram

```
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             │
      ┌────────────┐  ┌──────────┐       │
      │ CONFIRMED  │  │CANCELLED │ ◄─────┘
      └──────┬─────┘  └──────────┘
             │
     ┌────────┼─────────────┐
     ▼        ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│CHECKED_IN│ │CANCELLED │ │ NO_SHOW  │
└────┬─────┘ └──────────┘ └──────────┘
     │
     ▼
┌────────────┐
│CHECKED_OUT │
└────────────┘
```

**Simplified linear view:**

```
PENDING ──→ CONFIRMED ──→ CHECKED_IN ──→ CHECKED_OUT
   │              │
   └──→ CANCELLED ←┘
              ↑
    CONFIRMED ──→ NO_SHOW
```

### 5.2 Transition Enforcement

Every service method that changes a reservation's status calls the following guard before executing:

```python
def _validate_transition(reservation, new_status):
    current_status = reservation.status
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {allowed}"
        )
```

This guard is called **inside** the `@transaction.atomic` block so that any subsequent database writes only proceed if the transition is valid. The `InvalidTransitionError` is a custom exception defined in `reservations/exceptions.py` and is mapped to HTTP 409 Conflict in the API layer.

### 5.3 Terminal States

The following states are **terminal** — once a reservation reaches them, no further status changes are permitted:

| Terminal State | Meaning | Rooms Released? |
|---|---|---|
| `CHECKED_OUT` | Guest has departed; stay completed normally | Yes — status set to CLEANING |
| `CANCELLED` | Reservation was cancelled before or during the stay | Yes — rooms return to AVAILABLE |
| `NO_SHOW` | Guest did not arrive and reservation was not cancelled in time | Yes — rooms return to AVAILABLE |

All three states map to an empty list in `VALID_TRANSITIONS`, so any attempt to transition out of them raises `InvalidTransitionError`.

---

## 6. Service Methods | ٦. دوال وطرق طبقة الأعمال (Service Methods)

> 💡 **شرح طبقة الخدمات:** تحتوي على كافة العمليات المعقدة (`create`, `confirm`, `cancel`, `check_in`, `check_out`, `no_show`, `upgrade_room`) وتضمن عدم كتابة أي كود تعديل بيانات خارج هذه الدوال.

All methods live in `reservations/services.py` under the `ReservationService` class. Every method that writes to the database is decorated with `@transaction.atomic`.

### 6.1 `create(hotel, customer, room_ids, check_in, check_out, data)`

**Purpose:** Creates a new reservation with one or more rooms.

**Steps:**
1. Acquires row-level locks on the target rooms via `select_for_update()`.
2. Re-checks availability for the requested date range within the lock.
3. Raises `RoomNotAvailableError` if any room is already occupied.
4. Creates the `Reservation` record with status `PENDING`.
5. For each room, creates a `ReservationRoom` record with `nightly_price` snapshotted from `room.room_type.base_price`.
6. Returns the created `Reservation` instance.

**Raises:** `RoomNotAvailableError` if overlap detected; `ValidationError` if dates are invalid (e.g., check_out ≤ check_in).

---

### 6.2 `confirm(reservation)`

**Purpose:** Transitions a reservation from `PENDING` to `CONFIRMED`.

**Steps:**
1. Calls `_validate_transition(reservation, ReservationStatus.CONFIRMED)`.
2. Updates `reservation.status = CONFIRMED` and saves.
3. Optionally sends a confirmation notification (stub in Phase 5; implemented in Phase 8).

**Raises:** `InvalidTransitionError` if reservation is not in `PENDING` status.

---

### 6.3 `cancel(reservation, reason)`

**Purpose:** Transitions a reservation from `PENDING` or `CONFIRMED` to `CANCELLED`.

**Steps:**
1. Calls `_validate_transition(reservation, ReservationStatus.CANCELLED)`.
2. Updates `reservation.status = CANCELLED`.
3. Releases all associated rooms (sets their `Room.status` back to `AVAILABLE` if they were set to `OCCUPIED`).
4. Saves the reservation and all affected rooms.

**Raises:** `InvalidTransitionError` if reservation is not in `PENDING` or `CONFIRMED` status.

---

### 6.4 `check_in(reservation)`

**Purpose:** Transitions a reservation from `CONFIRMED` to `CHECKED_IN` and marks rooms as occupied.

**Steps:**
1. Calls `_validate_transition(reservation, ReservationStatus.CHECKED_IN)`.
2. Updates `reservation.status = CHECKED_IN`.
3. For each room in the reservation (non-deleted `ReservationRoom` records), sets `room.status = RoomStatus.OCCUPIED`.
4. Bulk-updates all affected rooms in a single query.

**Raises:** `InvalidTransitionError` if reservation is not in `CONFIRMED` status.

---

### 6.5 `check_out(reservation)`

**Purpose:** Transitions a reservation from `CHECKED_IN` to `CHECKED_OUT` and triggers post-checkout side effects.

**Steps:**
1. Calls `_validate_transition(reservation, ReservationStatus.CHECKED_OUT)`.
2. Updates `reservation.status = CHECKED_OUT`.
3. For each room in the reservation, sets `room.status = RoomStatus.CLEANING`.
4. Creates a `RoomCleaning` record for each room — in Phase 5, this is a **placeholder stub** via `_create_cleaning_tasks()`. The full cleaning workflow (task assignment, scheduling, completion tracking) is implemented in **Phase 7**.
5. Increments `reservation.customer.total_stays` by 1 and saves the customer record.

**Raises:** `InvalidTransitionError` if reservation is not in `CHECKED_IN` status.

> [!NOTE]
> The `_create_cleaning_tasks()` call in Phase 5 only creates the `RoomCleaning` record with status `PENDING`. The assignment to housekeeping staff and the full cleaning state machine are out of scope for this phase and are handled in Phase 7 (`rooms/services.py → CleaningService`).

---

### 6.6 `no_show(reservation)`

**Purpose:** Transitions a reservation from `CONFIRMED` to `NO_SHOW` when a guest fails to arrive.

**Steps:**
1. Calls `_validate_transition(reservation, ReservationStatus.NO_SHOW)`.
2. Updates `reservation.status = NO_SHOW`.
3. Releases all rooms back to `AVAILABLE` status (rooms were not physically occupied).

**Raises:** `InvalidTransitionError` if reservation is not in `CONFIRMED` status.

---

### 6.7 `upgrade_room(reservation, old_room, new_room, changed_by, reason)`

**Purpose:** Moves a guest from one room to another within an active reservation, with full audit logging and price recalculation.

**Steps:**
1. Validates that the reservation is in `CONFIRMED` or `CHECKED_IN` status.
2. Validates that `new_room` is available for the reservation's date range (calls `get_available_rooms()`).
3. Creates a `ReservationRoomChange` record with `room_from`, `room_to`, `price_before`, `price_after`, `changed_by`, and `reason`.
4. Soft-deletes the existing `ReservationRoom` for `old_room` (sets `is_deleted=True`, `deleted_at=now()`).
5. Creates a new `ReservationRoom` for `new_room` with a fresh `nightly_price` snapshot from `new_room.room_type.base_price`.
6. Updates `old_room.status = AVAILABLE` (or `CLEANING` if currently checked in).
7. Updates `new_room.status = OCCUPIED` if reservation is `CHECKED_IN`.

**Raises:** `RoomNotAvailableError` if new room is already occupied; `InvalidTransitionError` if reservation is in a terminal state.

---

## 7. Price Snapshot | ٧. مبدأ تجميد الأسعار وحمايتها المالية

> 💡 **شرح اللقطة السعرية:** الأسعار المتفق عليها وقت الحجز تُحفظ كأرقام نهائية ثابتة، ولا تتأثر بتغير خطط الأسعار أو المواسم المستقبلية.

### 7.1 What Is a Price Snapshot?

When a `ReservationRoom` record is created, the `nightly_price` field is populated from the current value of `room.room_type.base_price` at that exact moment. This value is then **frozen** — it becomes the authoritative price for that room for the duration of the reservation, regardless of any future changes to the room type's pricing.

```python
# In ReservationService.create()
nightly_price = room.room_type.base_price  # Snapshot captured here

ReservationRoom.objects.create(
    reservation=reservation,
    room=room,
    nightly_price=nightly_price,  # Stored immutably
    adults=adults,
    children=children,
)
```

### 7.2 Why Immutability Matters

| Scenario Without Snapshot | Impact |
|---|---|
| Hotel raises room prices after booking | Existing guests are incorrectly charged the new rate |
| Seasonal pricing changes mid-stay | Revenue reports show incorrect nightly revenue |
| Room type restructuring | Historical reservations show wrong prices |

By capturing the price at booking time and never overwriting it, the system guarantees:

- **Financial integrity:** Guests are charged exactly what they agreed to at booking.
- **Accurate historical reporting:** Revenue reports can always reproduce the exact figures for any past period.
- **Audit compliance:** The `price_before` and `price_after` fields in `ReservationRoomChange` provide a complete trail of any price changes during upgrades.

### 7.3 Price Recalculation on Upgrade

During a room upgrade, a **new price snapshot** is taken from the new room's type:

```python
new_nightly_price = new_room.room_type.base_price
nights = (reservation.check_out - reservation.check_in).days
price_difference = (new_nightly_price - old_nightly_price) * nights
```

The `price_difference` is recorded in `ReservationRoomChange` (as `price_after - price_before` per night, multiplied by nights) and may be used by the billing module in a later phase to generate a supplementary charge or credit.

---

## 8. Room Upgrade | ٨. آلية ترقية وتغيير الغرف

> 💡 **شرح الترقية:** إمكانية نقل النزيل لغرفة أخرى مع الحذف المرن للسجل القديم، وإنشاء سجل جديد، وتوثيق فرق السعر وتحديث الفاتورة الإجمالية ذرياً.

### 8.1 Upgrade Flow

The room upgrade process is a carefully orchestrated sequence of database operations, all executed within a single `@transaction.atomic` block to ensure atomicity:

```
1. Validate reservation is active (CONFIRMED or CHECKED_IN)
         │
         ▼
2. Validate new_room is available for reservation dates
         │
         ▼
3. Create ReservationRoomChange audit record
   (room_from, room_to, price_before, price_after, reason, changed_by)
         │
         ▼
4. Soft-delete old ReservationRoom
   (is_deleted=True, deleted_at=now())
         │
         ▼
5. Create new ReservationRoom with fresh price snapshot
         │
         ▼
6. Update old_room.status → AVAILABLE (or CLEANING)
         │
         ▼
7. Update new_room.status → OCCUPIED (if CHECKED_IN)
```

### 8.2 Price Difference Calculation

```python
old_price = old_reservation_room.nightly_price
new_price = new_room.room_type.base_price
nights = (reservation.check_out - reservation.check_in).days

price_difference_per_night = new_price - old_price
total_price_difference = price_difference_per_night * nights
```

Both `price_before` (= `old_price`) and `price_after` (= `new_price`) are stored per night in `ReservationRoomChange`. The total difference is computed at billing time by multiplying by the number of nights.

### 8.3 Soft-Delete vs. Hard Delete

Old `ReservationRoom` records are **soft-deleted** (not removed from the database) to preserve the audit trail. The availability engine filters out soft-deleted records via `is_deleted=False`, so they do not affect future availability queries. However, they remain visible in admin interfaces and financial audit queries.

---

## 9. API Endpoints | ٩. نقاط النهاية لواجهات الحجوزات (REST Endpoints)

> 💡 **شرح الـ Endpoints:** يغطي نقاط الاستعلام عن التوفر، إنشاء الحجوزات، تغيير الحالات عبر مسار `/status/`، وإجراء الترقية عبر `/upgrade-room/`.

All endpoints are prefixed with `/api/v1/reservations/` and require a valid JWT token. Permissions are evaluated per-hotel using the custom `HotelPermission` backend introduced in Phase 3.

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/reservations/` | List all reservations for the authenticated user's hotel | JWT + `reservations.view` |
| `POST` | `/api/v1/reservations/` | Create a new reservation | JWT + `reservations.manage` |
| `GET` | `/api/v1/reservations/{id}/` | Retrieve full detail of a specific reservation | JWT + `reservations.view` |
| `PATCH` | `/api/v1/reservations/{id}/` | Update reservation details (dates, special requests) | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/confirm/` | Transition reservation from PENDING to CONFIRMED | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/cancel/` | Cancel a PENDING or CONFIRMED reservation | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/check-in/` | Check in a CONFIRMED reservation | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/check-out/` | Check out a CHECKED_IN reservation | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/no-show/` | Mark a CONFIRMED reservation as no-show | JWT + `reservations.manage` |
| `POST` | `/api/v1/reservations/{id}/upgrade-room/` | Upgrade a room within an active reservation | JWT + `reservations.manage` |
| `GET` | `/api/v1/reservations/availability/` | Query available rooms for given hotel + date range | JWT + `reservations.view` |

### 9.1 Availability Endpoint Query Parameters

```
GET /api/v1/reservations/availability/?check_in=2024-06-01&check_out=2024-06-05&hotel_id=<uuid>
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `check_in` | `date` (ISO 8601) | Yes | Requested arrival date |
| `check_out` | `date` (ISO 8601) | Yes | Requested departure date |
| `hotel_id` | `UUID` | Yes | The hotel to check availability for |
| `room_type_id` | `UUID` | No | Filter results to a specific room type |

**Response:** A list of available `Room` objects with their current `RoomType`, `base_price`, and `status`.

---

## 10. Tests Summary | ١٠. ملخص نتائج الاختبارات الآلية (19 اختباراً ناجحاً)

> 💡 **ملخص الاختبارات:** 19 اختباراً تغطي سيناريوهات التداخل، الحالات المسموحة والممنوعة، حالات التزامن المتوازي، ترقية الغرف، والتأكد من إطلاق مهام التنظيف وزيادة عدد الإقامات.

Phase 5 includes **19 automated tests** covering all critical paths. Tests are located in `tests/test_reservations.py` and use Django's `TestCase` with `transaction.TestCase` for concurrency tests.

### Test Breakdown

| Category | Test Cases | Count |
|---|---|---|
| Availability overlap detection | Correct rooms excluded during overlap; edge cases (adjacent dates, same-day); non-active statuses do not block | 3 |
| Race condition simulation | Concurrent requests via threads; only one request succeeds, the other raises `RoomNotAvailableError` | 2 |
| State machine valid transitions | PENDING→CONFIRMED, PENDING→CANCELLED, CONFIRMED→CHECKED_IN, CONFIRMED→CANCELLED, CONFIRMED→NO_SHOW, CHECKED_IN→CHECKED_OUT | 6 |
| Invalid state machine transitions | PENDING→CHECKED_IN, CHECKED_OUT→CONFIRMED, CANCELLED→PENDING all raise `InvalidTransitionError` | 3 |
| Room upgrade | `ReservationRoomChange` record created with correct fields; `nightly_price` updated to new room's price | 2 |
| Checkout side effects | `Room.status` set to `CLEANING` after checkout; `customer.total_stays` incremented; `RoomCleaning` record created | 3 |
| **Total** | | **19** |

### Key Test Scenarios

**Overlap detection — adjacent dates (edge case):**
```python
# A checkout on day 5 and a new check-in on day 5 should NOT overlap
# (checkout is exclusive; the room is free from check_out date onward)
existing: check_in=June 1, check_out=June 5
new request: check_in=June 5, check_out=June 8
# Expected: room IS available (June 5 is not double-booked)
```

**Race condition test:**
```python
# Using threading.Barrier to synchronize two threads at the availability check
# so both see the room as available simultaneously
# Expected: exactly one succeeds, one raises RoomNotAvailableError
```

**Checkout side effects:**
```python
# After check_out():
assert room.status == RoomStatus.CLEANING
assert customer.total_stays == previous_total_stays + 1
assert RoomCleaning.objects.filter(room=room, reservation=reservation).exists()
```

---

## 11. Files Changed | ١١. جدول الملفات المنشأة والمعدلة

> 💡 **دليل الملفات:** يشمل ملفات تطبيق `reservations` وملفات التهيئة والاختبارات المضافة في هذه المرحلة.

| File | Action | What Changed |
|---|---|---|
| `reservations/models.py` | **CREATED** | `Reservation`, `ReservationRoom`, `ReservationRoomChange` models; `ReservationStatus` TextChoices; `VALID_TRANSITIONS` dict; composite index on `ReservationRoom` |
| `reservations/services.py` | **CREATED** | `ReservationService` class with `create`, `confirm`, `cancel`, `check_in`, `check_out`, `no_show`, `upgrade_room` methods; `_validate_transition` guard; `_create_cleaning_tasks` stub |
| `reservations/selectors.py` | **CREATED** | `get_available_rooms(hotel, check_in, check_out)` availability engine; `get_reservation_list(hotel, filters)` list selector with optional status/date filtering |
| `reservations/serializers.py` | **CREATED** | `ReservationSerializer` with nested `ReservationRoomSerializer`; `ReservationCreateSerializer` accepting `room_ids`, `check_in`, `check_out`; `RoomUpgradeSerializer` |
| `reservations/views.py` | **CREATED** | `ReservationViewSet` with standard CRUD plus custom actions: `confirm`, `cancel`, `check_in`, `check_out`, `no_show`, `upgrade_room`, `availability` |
| `reservations/urls.py` | **CREATED** | `DefaultRouter` registration for `ReservationViewSet` at `/api/v1/reservations/` |
| `reservations/exceptions.py` | **CREATED** | `RoomNotAvailableError` (HTTP 409); `InvalidTransitionError` (HTTP 409); base `ReservationError` |
| `rooms/models.py` | **MODIFIED** | Added `OCCUPIED`, `CLEANING`, and `MAINTENANCE` to `RoomStatus` TextChoices (previously only `AVAILABLE` and `OUT_OF_ORDER` existed) |
| `rooms/services.py` | **MODIFIED** | Added `_check_no_blocking_issues()` placeholder that raises `RoomBlockedError` if a room is in `OCCUPIED` or `CLEANING` status and a conflicting operation is attempted |
| `tests/test_reservations.py` | **CREATED** | 19 reservation tests covering availability, race conditions, state machine, room upgrade, and checkout side effects |

---

## 12. Migrations | ١٢. ترحيلات قاعدة البيانات للمرحلة الخامسة

> 💡 **شرح المايجريشن:** يوثق إنشاء جداول `reservations_reservation` و `reservations_reservationroom` مع القيود والفهارس المركبة.

### `reservations/migrations/0001_initial.py`

**Action:** Creates the initial schema for the reservations app.

**Tables created:**

| Table | Model | Notes |
|---|---|---|
| `reservations_reservation` | `Reservation` | UUID PK; FKs to hotel, customer, booking_source, created_by; check_in/check_out date fields; status with default PENDING |
| `reservations_reservationroom` | `ReservationRoom` | UUID PK; FKs to reservation and room; nightly_price decimal(10,2); soft-delete fields |
| `reservations_reservationroomchange` | `ReservationRoomChange` | UUID PK; FKs to reservation, room_from, room_to, changed_by; price fields; auto-timestamp |

**Indexes created:**

```python
migrations.AddIndex(
    model_name='reservationroom',
    index=models.Index(
        fields=['room', 'is_deleted'],
        name='reservationroom_room_deleted_idx'
    ),
),
```

**Foreign key dependencies:**

This migration depends on:
- `hotels/migrations/0001_initial.py` — for the `Hotel` model
- `customers/migrations/0001_initial.py` — for the `Customer` model
- `rooms/migrations/0001_initial.py` — for the `Room` model
- `users/migrations/0001_initial.py` — for the `User` model (created_by, changed_by fields)

> [!NOTE]
> The migration for `rooms/0002_add_occupied_cleaning_status.py` (adding `OCCUPIED` and `CLEANING` to `RoomStatus`) must be run **before** `reservations/migrations/0001_initial.py` in environments that apply migrations incrementally. The recommended approach is `python manage.py migrate` which resolves the dependency graph automatically.

**Migration command:**

```bash
python manage.py makemigrations reservations
python manage.py migrate reservations
```

**Rollback command:**

```bash
python manage.py migrate reservations zero
```

> [!CAUTION]
> Rolling back `reservations/migrations/0001_initial.py` will **drop all reservation data**. Only perform this in development or staging environments. Never roll back this migration in production without a full database backup.

---

*End of Phase 5 Documentation*
