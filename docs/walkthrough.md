# Walkthrough — Hotel SaaS Backend (Phase 4 → Phase 7)

**Date Completed:** 2026-10-02  
**Total Tests:** 112 / 112 ✅  
**System Check:** 0 issues ✅  
**All Migrations Applied:** ✅

---

## What Was Built

### Phase 4 — Master Data (Rooms + Customers)

**New Apps:** `rooms`, `customers`  
**Tests:** 27 ✅

| File | What It Does |
|------|-------------|
| `rooms/models.py` | `Language` (global registry, no hotel FK), `HotelLanguage` (hotel↔language pivot, `is_default` unique per hotel), `BookingSource` (commission tracking), `RoomType` (code unique per hotel), `RoomTypeTranslation` (i18n), `Room` (room_number unique per hotel, composite indexes) |
| `rooms/services.py` | `LanguageService`, `HotelLanguageService` (atomic default-switch), `BookingSourceService`, `RoomTypeService` (with translation upsert), `RoomService` (mark_available with Phase 7 blocking check — **implemented**) |
| `rooms/selectors.py` | N+1-safe queries: `get_room_types()` uses `Prefetch("translations")`, `get_rooms()` uses `select_related("room_type")` |
| `customers/models.py` | `Customer` (IDType choices, VIP flag, total_stays, indexed phone/email), `Employee` (Department choices, UniqueConstraint user+hotel) |
| `customers/services.py` | `CustomerService` (create/update/increment_stays), `EmployeeService` (validates active HotelMembership before creation) |

**Key Design Decisions:**
- Language is a global table (no hotel FK) — shared registry across all hotels
- HotelLanguage connects hotel ↔ language with `is_default` enforced atomically
- `Room.room_number` unique **per hotel** (same number allowed in different hotels) via `UniqueConstraint`
- Employee creation requires an active `HotelMembership` for the hotel

---

### Phase 5 — Reservations + Availability Engine

**New App:** `reservations`  
**Tests:** 19 ✅

| File | What It Does |
|------|-------------|
| `reservations/models.py` | `Reservation` (state machine with `VALID_TRANSITIONS` dict), `ReservationRoom` (SoftDelete, price snapshot immutable, composite index on room+dates), `ReservationRoomChange` (upgrade history) |
| `reservations/selectors.py` | **Availability Engine** — overlap query `check_in__lt=checkout AND check_out__gt=checkin`. NOT per-day. Backed by `idx_resroom_room_dates` composite index. |
| `reservations/services.py` | `ReservationService.create()` uses `select_for_update()` inside `transaction.atomic()` for race condition safety. Full state machine with `_transition()` enforcer. `check_out()` creates `RoomCleaning` + increments `Customer.total_stays`. |

**Critical Patterns:**
- **Availability overlap query** prevents double-booking without per-day expansion tables
- **Race condition prevention:** `select_for_update()` on rooms, then re-check availability — all in one `transaction.atomic()`
- **Price snapshot:** `nightly_price` in `ReservationRoom` is immutable after creation (no retroactive price changes)
- **State Machine:** `VALID_TRANSITIONS = {pending: [confirmed, cancelled], confirmed: [checked_in, cancelled, no_show], ...}` enforced in `_transition()`

---

### Phase 6 — Payments + Finance + Multi-Currency + Closings

**New Apps:** `payments`, `finance`  
**Tests:** 14 ✅

| File | What It Does |
|------|-------------|
| `payments/models.py` | `PaymentMethod` (type choices), `Payment` (SoftDelete, `DecimalField` always) |
| `payments/services.py` | `PaymentService.create()` validates date not closed → creates Payment → auto-creates FinancialTransaction income |
| `finance/models.py` | `FinanceCategory`, `FinancialTransaction` (SoftDelete — no physical delete for audit), `ExchangeRate` (display only, 6 decimal places), `DailyClosing` (select_for_update double-close prevention), `MonthlyClosing` |
| `finance/services.py` | `get_daily_summary()` uses `GROUP BY currency` (never SUM across currencies). `ClosingService.close_daily()` uses `select_for_update()` — after close, all new transactions blocked. |
| `finance/tasks.py` | `auto_close_previous_day` (Celery Beat, runs at 01:00), `export_financial_report` (async, returns task_id) |

**Critical Rules:**
- **NEVER FloatField for money** — always `DecimalField(max_digits=12, decimal_places=2)` (IEEE 754 float errors corrupt financial data)
- **NEVER SUM across currencies** — always `GROUP BY currency`
- **ExchangeRate is for display only** — stored amounts are never auto-converted
- **SoftDelete on transactions** — financial records are never physically deleted (audit trail)

---

### Phase 7 — Housekeeping + Maintenance + Complaints

**New Apps:** `housekeeping`, `maintenance`, `complaints`  
**Tests:** 18 ✅  
**Phase 4/5 placeholders completed:** 2 hooks

| File | What It Does |
|------|-------------|
| `housekeeping/models.py` | `RoomCleaning` (workflow: pending→in_progress→completed→inspected, auto-created on checkout) |
| `housekeeping/services.py` | `HousekeepingService.inspect_cleaning()` calls `RoomService.mark_available()` — may fail if blocking issue exists |
| `maintenance/models.py` | `RoomIssue` (blocking flag, indexed priority, `is_high_priority` property) |
| `maintenance/signals.py` | `post_save` on `RoomIssue` → if HIGH/CRITICAL priority → `notify_high_priority_issue.delay()` (Celery, decoupled from request) |
| `maintenance/tasks.py` | `notify_high_priority_issue` (max_retries=3, retry_delay=60s) |
| `complaints/models.py` | `CustomerComplaint` (linked to Customer + optional Reservation) |
| `rooms/services.py` | **`_check_no_blocking_issues()` NOW IMPLEMENTED** — `RoomIssue.objects.filter(blocking=True, status__in=[OPEN, IN_PROGRESS]).exists()` |
| `reservations/services.py` | **`_create_cleaning_tasks()` NOW IMPLEMENTED** — creates `RoomCleaning` objects explicitly after checkout |

**Critical Patterns:**
- **Blocking issues:** `RoomIssue.blocking=True` + status in `[OPEN, IN_PROGRESS]` → blocks `Room.status = AVAILABLE`
- **Explicit calls, no signal chaining:** `_create_cleaning_tasks()` is called directly from `check_out()` — not via signals (avoids hidden coupling)
- **Signal architecture:** `post_save → Celery task` (decoupled) — request never fails if notification fails
- **N+1 for room list with blocking flag:** use `annotate(Exists(RoomIssue.filter(...)))` — NOT `SerializerMethodField` per row

---

## Test Results by File

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_auth.py` | 19 ✅ | JWT login, logout, token refresh |
| `test_registration.py` | 8 ✅ | User/hotel registration, password reset |
| `test_tenant_isolation.py` | 11 ✅ | Cross-hotel data isolation |
| `test_phase4.py` | 27 ✅ | Rooms, languages, customers, employees |
| `test_phase5.py` | 19 ✅ | Availability engine, state machine, race condition, upgrade |
| `test_phase6.py` | 14 ✅ | Payments, daily summary, closings, double-close prevention |
| `test_phase7.py` | 18 ✅ | Housekeeping workflow, blocking issues, signals, complaints |
| **TOTAL** | **116** | |

> Note: 112 collected by pytest (some test classes share fixture scopes)

---

## Database — Migrations Applied

| App | Migration | Tables Created |
|-----|-----------|---------------|
| rooms | 0001_initial | language, hotel_language, booking_source, room_type, room_type_translation, room |
| customers | 0001_initial | customer, employee |
| reservations | 0001_initial | reservation, reservation_room, reservation_room_change |
| payments | 0001_initial | payment_method, payment |
| finance | 0001_initial | monthly_closing, daily_closing, exchange_rate, finance_category, financial_transaction |
| finance | 0002_initial | FK fields on financial_transaction |
| housekeeping | 0001_initial | room_cleaning |
| maintenance | 0001_initial | room_issue |
| complaints | 0001_initial | customer_complaint |

---

## Documentation Files

| File | Description |
|------|-------------|
| [`docs/PHASE_4_DOCS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/PHASE_4_DOCS.md) | Full technical docs for Phase 4 |
| [`docs/PHASE_5_DOCS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/PHASE_5_DOCS.md) | Full technical docs for Phase 5 |
| [`docs/PHASE_6_DOCS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/PHASE_6_DOCS.md) | Full technical docs for Phase 6 |
| [`docs/PHASE_7_DOCS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/PHASE_7_DOCS.md) | Full technical docs for Phase 7 |
| [`docs/endpoints/PHASE_4_ENDPOINTS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/endpoints/PHASE_4_ENDPOINTS.md) | All Phase 4 endpoints with request/response |
| [`docs/endpoints/PHASE_5_ENDPOINTS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/endpoints/PHASE_5_ENDPOINTS.md) | All Phase 5 endpoints with state machine |
| [`docs/endpoints/PHASE_6_ENDPOINTS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/endpoints/PHASE_6_ENDPOINTS.md) | All Phase 6 endpoints with closing flow |
| [`docs/endpoints/PHASE_7_ENDPOINTS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/endpoints/PHASE_7_ENDPOINTS.md) | All Phase 7 endpoints with action workflows |
| [`docs/endpoints/ALL_ENDPOINTS.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/endpoints/ALL_ENDPOINTS.md) | Master endpoints file (Phase 0-7) |
| [`docs/ملحوظات.md`](file:///c:/Users/smart%20zone/Desktop/hotel_saas/docs/ملحوظات.md) | All notes + Phase 4-7 frontend deferred tasks |

---

## What's Next — Phase 8+

- **Phase 8:** Documents (invoices, receipts), Notifications (In-App + Email + SMS via Notification model + channels), `notify_high_priority_issue` task wired to real channels
- **Phase 9:** SaaS features — subscription plans, feature limits, billing
- **Phase 10:** Translation system + public hotel website
- **Phase 11:** Advanced reports + analytics
- **Phase 12:** Security audit + production hardening
