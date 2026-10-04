# Phase 6 — Payments + Finance + Multi-Currency + Closings
# المرحلة السادسة — المدفوعات والماليات وتعدد العملات والإغلاقات الدورية

---

## 1. Overview | ١. نظرة عامة شاملة على النظام المالي

> [!NOTE]
> 💡 **شرح باللغة العربية (Overview):**
> تمثل المرحلة السادسة النظام المالي والمحاسبي المتكامل لمنصة إدارة الفنادق.
> يوفر هذا النظام بنية قوية لتسجيل مدفوعات النزلاء، الإنشاء التلقائي لقيود اليومية في دفتر المعاملات المالية، دعم العملات المتعددة مع العزل التام للمبالغ، وإجراء الإغلاقات اليومية والشهرية بدقة محاسبية متناهية تمنع أي تلاعب أو تضارب.

Phase 6 implements the complete **payment and financial accounting system** for the Hotel SaaS platform. This phase introduces all infrastructure required to record guest payments, automatically generate corresponding financial transactions, aggregate financial data across multiple currencies, and produce auditable daily and monthly closings.

### Scope

| Area | What Is Built |
|---|---|
| **Payments** | `PaymentMethod` catalogue, `Payment` recording with soft-delete, auto-creation of `FinancialTransaction` on every payment |
| **Finance** | `FinanceCategory`, `FinancialTransaction` (income/expense ledger), `ExchangeRate` reference table |
| **Closings** | `DailyClosing` and `MonthlyClosing` with idempotency guards, `select_for_update` concurrency protection |
| **Async** | Celery tasks for automatic daily closing (`auto_close_previous_day`) and async report export (`export_financial_report`) |
| **Multi-Currency** | All aggregations grouped by currency; cross-currency sums are strictly forbidden |

### Design Priorities

1. **Financial correctness is the highest priority.** Every monetary value is stored as `DecimalField` (PostgreSQL `NUMERIC`). `FloatField` is never used for money.
2. **No cross-currency aggregation.** Totals are always broken down by currency. Exchange rates are display-only and never participate in financial calculations.
3. **Audit trail preservation.** `FinancialTransaction` records are never physically deleted. Soft-delete sets `is_deleted=True` and `deleted_at` only. The underlying row is retained permanently.
4. **Idempotency.** Closing operations are guarded by `select_for_update()` inside `transaction.atomic` to prevent race conditions and double-closes.
5. **Async offloading.** Long-running export operations run as Celery tasks, returning a `task_id` immediately so the API stays responsive.

---

## 2. Models

### 2.1 `PaymentMethod` | طرق ووسائل الدفع المعتمدة

> 💡 **شرح المودل بالعربية (Payment Method):**
> يمثل وسائل الدفع المتاحة داخل الفندق (كاش، بطاقات ائتمانية، تحويل بنكي، بوابات دفع أونلاين).
> كل وسيلة دفع مرتبطة بالفندق ومعرفة باسم فريد داخل الفندق الواحد.

Represents the payment instruments available at a hotel (e.g., Cash, Credit Card, Bank Transfer).

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `hotel` | `ForeignKey(Hotel)` | NOT NULL, on_delete=CASCADE | Scoped to a single hotel |
| `name` | `CharField(max_length=100)` | NOT NULL | e.g., "Cash", "Visa Card" |
| `is_active` | `BooleanField` | default=True | Inactive methods hidden from recording UI |
| `created_at` | `DateTimeField` | auto_now_add=True | Immutable creation timestamp |

**Indexes:** `(hotel, name)` unique together — a hotel cannot have two methods with the same name.

---

### 2.2 `Payment` | سجل المدفوعات والمقبوضات

> 💡 **شرح المودل بالعربية (Payment):**
> السجل المركزي لكل عملية دفع يتلقاها الفندق. يرتبط بالحجز ووسيلة الدفع والمبلغ والعملة.
> يعتمد مبدأ الحذف المرن (`SoftDeleteModel`) لحماية السجلات المالية من الحذف، ويستخدم `DecimalField` حصراً.

The central record of a financial payment received by the hotel.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `hotel` | `ForeignKey(Hotel)` | NOT NULL, on_delete=CASCADE | Owner hotel |
| `reservation` | `ForeignKey(Reservation)` | nullable, on_delete=SET_NULL | Optional — payments may not be tied to a reservation |
| `payment_method` | `ForeignKey(PaymentMethod)` | NOT NULL, on_delete=PROTECT | Method used; PROTECT prevents deletion of used methods |
| `amount` | `DecimalField(max_digits=10, decimal_places=2)` | NOT NULL | Exact monetary value — **never FloatField** |
| `currency` | `CharField(max_length=3)` | NOT NULL | ISO 4217 code, e.g., "USD", "EUR" |
| `payment_date` | `DateField` | NOT NULL | Business date of the payment |
| `reference_number` | `CharField(max_length=100)` | blank=True | External reference (POS receipt, bank ref) |
| `notes` | `TextField` | blank=True | Free-text notes |
| `recorded_by` | `ForeignKey(User)` | NOT NULL, on_delete=PROTECT | Staff member who recorded the payment |
| `is_deleted` | `BooleanField` | default=False | Soft-delete flag |
| `deleted_at` | `DateTimeField` | nullable | Set when soft-deleted |
| `created_at` | `DateTimeField` | auto_now_add=True | Immutable creation timestamp |

> [!CAUTION]
> **Physical deletion of `Payment` records is never permitted.** Only soft-delete (`is_deleted=True`) is allowed. Financial records must be retained for audit and regulatory purposes.

**Manager:** A custom `ActivePaymentManager` filters `is_deleted=False` by default. Use `Payment.all_objects.all()` to include soft-deleted records.

---

### 2.3 `FinanceCategory` | بنود وتصنيفات الإيرادات والمصروفات

> 💡 **شرح المودل بالعربية (Finance Category):**
> تصنيف مالي للإيرادات (مثل إيرادات الغرف، المطعم) والمصروفات (مثل الكهرباء، الصيانة، الرواتب)، لتسهيل استخراج التقارير التحليلية المفصلة.

Classifies financial transactions (e.g., Room Revenue, F&B Income, Maintenance Expense).

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `hotel` | `ForeignKey(Hotel)` | NOT NULL, on_delete=CASCADE | Scoped to a single hotel |
| `name` | `CharField(max_length=100)` | NOT NULL | Category label |
| `category_type` | `CharField(max_length=10)` | choices=[`INCOME`, `EXPENSE`] | Determines ledger side |
| `is_active` | `BooleanField` | default=True | Inactive categories hidden from transaction creation UI |

**Indexes:** `(hotel, name)` unique together.

---

### 2.4 `FinancialTransaction` | قيود المعاملات المالية (دفتر اليومية)

> 💡 **شرح المودل بالعربية (General Ledger Transaction):**
> يمثل القيد المحاسبي الموثق لكل حركة مالية. يتم إنشاؤه تلقائياً فور تسجيل أي دفعة (Payment) لضمان مطابقة الإيرادات.
> **قاعدة حيوية:** ممنوع الحذف الفيزيائي (Physical Delete) لهذه السجلات نهائياً لحفظ المسار التدقيقي (Audit Trail).

The immutable accounting ledger. Every `Payment` automatically creates a corresponding `FinancialTransaction`. Additional manual entries can also be created directly.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `hotel` | `ForeignKey(Hotel)` | NOT NULL, on_delete=CASCADE | Owner hotel |
| `category` | `ForeignKey(FinanceCategory)` | NOT NULL, on_delete=PROTECT | Accounting category |
| `related_payment` | `ForeignKey(Payment)` | nullable, on_delete=SET_NULL | Link to source payment, if auto-generated |
| `amount` | `DecimalField(max_digits=10, decimal_places=2)` | NOT NULL | Exact monetary value |
| `currency` | `CharField(max_length=3)` | NOT NULL | ISO 4217 code |
| `transaction_date` | `DateField` | NOT NULL | Business date of the transaction |
| `description` | `TextField` | NOT NULL | Human-readable description |
| `transaction_type` | `CharField(max_length=10)` | choices=[`INCOME`, `EXPENSE`] | Ledger side |
| `is_deleted` | `BooleanField` | default=False | Soft-delete flag |
| `deleted_at` | `DateTimeField` | nullable | Set when soft-deleted |
| `created_at` | `DateTimeField` | auto_now_add=True | Immutable creation timestamp |

> [!CAUTION]
> **Physical deletion of `FinancialTransaction` records is absolutely forbidden.** The audit trail must be preserved at all times. Any "deletion" via the API only sets `is_deleted=True` and `deleted_at=now()`. The row remains in the database permanently. Queries for active transactions filter `is_deleted=False`.

---

### 2.5 `ExchangeRate` | أسعار صرف العملات

> 💡 **شرح المودل بالعربية (Exchange Rate):**
> جدول مرجعي لأسعار الصرف بين العملات بدقة 6 خانات عشرية. يُستخدم **لأغراض العرض فقط** في الواجهات، ولا يتدخل في تحويل القيود المالية المخزنة تلقائياً.

Stores currency exchange rates for **display purposes only**.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `from_currency` | `CharField(max_length=3)` | NOT NULL | Source ISO 4217 currency code |
| `to_currency` | `CharField(max_length=3)` | NOT NULL | Target ISO 4217 currency code |
| `rate` | `DecimalField(max_digits=12, decimal_places=6)` | NOT NULL | Exchange rate with 6 decimal precision |
| `date` | `DateField` | NOT NULL | The date this rate is valid for |
| `source` | `CharField(max_length=100)` | NOT NULL | Rate source (e.g., "ECB", "manual") |

> [!IMPORTANT]
> `ExchangeRate` is used **exclusively for display purposes** — for example, showing an approximate consolidated total on a dashboard. It is **never** used in financial calculations, closings, or any aggregation that affects stored financial data.

**Indexes:** `(from_currency, to_currency, date)` unique together.

---

### 2.6 `DailyClosing` | إغلاق اليوم المالي (Daily Closing)

> 💡 **شرح المودل بالعربية (Daily Closing):**
> يوثق إقفال اليوم المالي للفندق ويحتسب إجمالي الإيرادات والمصروفات وصافي الدخل. محمي بقفل قاعدة البيانات `select_for_update` لمنع الإغلاق المزدوج، ويمنع إضافة أي معاملات جديدة لتاريخ مغلق.

Represents the end-of-day financial close for a specific hotel and date.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `hotel` | `ForeignKey(Hotel)` | NOT NULL, on_delete=CASCADE | Owner hotel |
| `date` | `DateField` | NOT NULL | The business date being closed |
| `status` | `CharField(max_length=10)` | choices=[`OPEN`, `CLOSED`], default=`OPEN` | Closing status |
| `total_income_by_currency` | `JSONField` | default=dict | e.g., `{"USD": "1500.00", "EUR": "200.00"}` |
| `total_expense_by_currency` | `JSONField` | default=dict | e.g., `{"USD": "300.00"}` |
| `closed_by` | `ForeignKey(User)` | nullable, on_delete=SET_NULL | User who performed the close; NULL for auto-close |
| `closed_at` | `DateTimeField` | nullable | Timestamp when close was performed |

**Constraints:**
- `UniqueConstraint(fields=['hotel', 'date'])` — one closing record per hotel per date.
- `select_for_update()` is used on every read that precedes a status change to prevent concurrent double-closes.

**Behavior after CLOSED:**
- `PaymentService.create()` raises `DateClosedError` if `payment_date` matches a `CLOSED` daily closing.
- No new `FinancialTransaction` records can be posted to a closed date.

---

### 2.7 `MonthlyClosing` | إغلاق الشهر المالي (Monthly Closing)

> 💡 **شرح المودل بالعربية (Monthly Closing):**
> يجمع نتائج الإغلاقات اليومية لكامل الشهر لتوثيق الحسابات الختامية الشهرية وتأكيد سلامة القيود.

Represents the end-of-month financial close for a specific hotel, year, and month.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUIDField` | PK, default=uuid4 | Globally unique identifier |
| `hotel` | `ForeignKey(Hotel)` | NOT NULL, on_delete=CASCADE | Owner hotel |
| `year` | `IntegerField` | NOT NULL | Gregorian year (e.g., 2026) |
| `month` | `IntegerField` | NOT NULL | Month number 1–12 |
| `status` | `CharField(max_length=10)` | choices=[`OPEN`, `CLOSED`], default=`OPEN` | Closing status |
| `total_income_by_currency` | `JSONField` | default=dict | Aggregated from all daily closings |
| `total_expense_by_currency` | `JSONField` | default=dict | Aggregated from all daily closings |
| `closed_by` | `ForeignKey(User)` | nullable, on_delete=SET_NULL | User who performed the close |
| `closed_at` | `DateTimeField` | nullable | Timestamp when close was performed |

**Constraints:**
- `UniqueConstraint(fields=['hotel', 'year', 'month'])` — one monthly closing record per hotel per month.
- **Prerequisite:** `ClosingService.close_monthly()` raises `UnclosedDailyClosingsError` if any `DailyClosing` for the given hotel/year/month does not have `status=CLOSED`.

---

## 3. GOLDEN RULE: DecimalField for ALL Money | ٣. القاعدة الذهبية: استخدام DecimalField حصراً لكافة الحقول المالية

> [!WARNING]
> 💡 **تحذير هندسي بالغ الأهمية:**
> استخدام `FloatField` للأموال يُعد خطأً معمارياً فادحاً يسبب أخطاء تقريب بنكية وكسور سنتات تختفي أو تظهر من العدم بسبب طريقة تمثيل الفاصلة العائمة في المعالجات (IEEE 754)!
> **القاعدة الصارمة:** استخدام `DecimalField(max_digits=12, decimal_places=2)` دائماً، والذي يتحول في PostgreSQL إلى نوع `NUMERIC` عالي الدقة.

> [!WARNING]
> **Every monetary amount MUST be stored in a `DecimalField`. Using `FloatField` for money is a critical bug that will cause financial data corruption.**

### Why FloatField Is Dangerous for Money

IEEE 754 double-precision floating-point arithmetic cannot represent all decimal fractions exactly. This is a fundamental property of binary floating-point representation, not a Python bug.

**Python demonstration:**

```python
>>> 0.1 + 0.2
0.30000000000000004

>>> 0.1 + 0.2 == 0.3
False
```

In isolation, the error `0.000000000000000004` seems negligible. However, in a financial system processing thousands of transactions daily, these errors **compound**. A rounding discrepancy of a fraction of a cent per transaction can accumulate to significant errors over time — enough to cause balance mismatches, failed audits, and regulatory non-compliance.

### PostgreSQL Type Mapping

| Django Field | PostgreSQL Type | Exact? | Use for Money? |
|---|---|---|---|
| `DecimalField` | `NUMERIC(p, s)` | ✅ Yes — arbitrary precision | ✅ Always |
| `FloatField` | `DOUBLE PRECISION` | ❌ No — binary floating point | ❌ Never |

PostgreSQL's `NUMERIC` type stores the exact decimal representation as specified. `0.10 + 0.20` in a `NUMERIC` column yields exactly `0.30`.

### Correct vs. Incorrect Field Declaration

```python
# WRONG — FloatField loses precision
amount = models.FloatField()  # 0.1 + 0.2 → 0.30000000000000004

# CORRECT — DecimalField is exact
amount = models.DecimalField(max_digits=10, decimal_places=2)  # 0.10 + 0.20 → 0.30
```

### Python `Decimal` Type in Application Code

When constructing monetary values in Python code, always use `decimal.Decimal`, never `float`:

```python
from decimal import Decimal

# WRONG
amount = 1500.50  # float

# CORRECT
amount = Decimal('1500.50')  # Decimal — exact
```

Django's ORM automatically returns `DecimalField` values as `decimal.Decimal` objects, so database reads are safe by default. The risk is in application logic that constructs values directly.

---

## 4. Multi-Currency Architecture | ٤. معمارية تعدد العملات وحظر جمع العملات المختلفة

> [!IMPORTANT]
> 💡 **القاعدة المحاسبية لتعدد العملات:**
> ممنوع جمع مبالغ من عملات مختلفة نهائياً! لا تجمع 100 دولار + 50 يورو وتكتب 150.
> يتم التجميع دائماً عبر `GROUP BY currency`، لترجع التقارير ملخصاً لكل عملة على حدة (إيراد USD، إيراد EUR، وهكذا).

### Core Rule: Never Sum Across Currencies

The most critical architectural constraint in Phase 6: **it is meaningless to add amounts in different currencies together.** Adding 1,500 USD and 200 EUR to get "1,700" is not a valid financial figure — it is an arbitrary number with no financial meaning.

All financial aggregations in this system **must group by currency at the database level**.

### Wrong vs. Correct Aggregation Pattern

```python
from django.db.models import Sum

# WRONG — sums across currencies, produces a meaningless total
total = Payment.objects.filter(hotel=hotel).aggregate(total=Sum('amount'))
# Returns: {'total': Decimal('1700.00')} ← This number means nothing

# CORRECT — group by currency, each total is meaningful
totals = Payment.objects.filter(hotel=hotel).values('currency').annotate(
    total=Sum('amount')
)
# Returns: [
#   {'currency': 'USD', 'total': Decimal('1500.00')},
#   {'currency': 'EUR', 'total': Decimal('200.00')}
# ]
```

This pattern is applied consistently throughout:
- `FinanceService.get_daily_summary()` — groups transactions by `(currency, transaction_type)`
- `ClosingService.close_daily()` — stores `total_income_by_currency` and `total_expense_by_currency` as JSON dicts keyed by currency
- `ClosingService.close_monthly()` — aggregates daily closing JSON dicts per currency

### Exchange Rates: Display Only

`ExchangeRate` records are stored to support dashboard features such as "show approximate total in hotel base currency." This conversion is:

- Applied **after** the real per-currency totals are computed
- Clearly labeled as "approximate" in the UI
- **Never** written back to any financial record
- **Never** used in closing calculations

### API Response Format for Financial Summaries

All endpoints returning financial summaries use a consistent dict-keyed-by-currency format:

```json
{
  "USD": {
    "income": "1500.00",
    "expense": "200.00",
    "net": "1300.00"
  },
  "EUR": {
    "income": "200.00",
    "expense": "50.00",
    "net": "150.00"
  }
}
```

All monetary values in API responses are serialized as strings to prevent JSON floating-point precision loss in client-side JavaScript.

---

## 5. Service Layer | ٥. طبقة الخدمات المحاسبية وإدارة الإغلاقات

> 💡 **شرح طبقة الخدمات:** تشمل `PaymentService` (تسجيل الدفع والربط التلقائي بالمعاملات)، `FinanceService` (استخراج الملخصات والتحقق من عدم إغلاق التاريخ)، و `ClosingService` (تنفيذ الإغلاق اليومي والشهري الذري ومنع التضارب).

### 5.1 `PaymentService.create(hotel, reservation, data)`

**Purpose:** Records a new payment and automatically creates the corresponding `FinancialTransaction`.

**Steps:**

1. **Validate `payment_date`** — Check whether a `DailyClosing` exists for `(hotel, payment_date)` with `status=CLOSED`. If so, raise `DateClosedError`. New payments cannot be posted to a closed date.
2. **Create `Payment`** — Persist the `Payment` record with all provided fields.
3. **Auto-create `FinancialTransaction`** — Automatically create a `FinancialTransaction` record linked to the new payment, with `transaction_type=INCOME`, `amount` and `currency` copied from the payment, and a generated description.
4. **Return** the created `Payment` instance.

**Error Cases:**

| Exception | Condition |
|---|---|
| `DateClosedError` | `payment_date` falls on a `DailyClosing` with `status=CLOSED` |
| `ValidationError` | Missing required fields, invalid currency code, negative amount |

---

### 5.2 `FinanceService.get_daily_summary(hotel, date)`

**Purpose:** Computes the income/expense summary for a given hotel and date, grouped by currency.

**Implementation:**

- Queries `FinancialTransaction.objects.filter(hotel=hotel, transaction_date=date, is_deleted=False)`
- Groups by `(currency, transaction_type)` using `.values('currency', 'transaction_type').annotate(total=Sum('amount'))`
- Builds and returns a dict with the structure:

```python
{
    "USD": {"income": Decimal("1500.00"), "expense": Decimal("200.00"), "net": Decimal("1300.00")},
    "EUR": {"income": Decimal("200.00"), "expense": Decimal("0.00"),   "net": Decimal("200.00")},
}
```

---

### 5.3 `ClosingService.close_daily(hotel, date, closed_by)`

**Purpose:** Performs the daily financial close for a hotel and date.

**Concurrency and Idempotency:**

- Uses `select_for_update()` on the `DailyClosing` row to obtain a pessimistic row-level lock.
- If `status == CLOSED`, immediately raises `AlreadyClosedError` — the operation is idempotent.
- Entire operation runs inside `transaction.atomic` to guarantee atomicity.

**Code Skeleton:**

```python
@transaction.atomic
def close_daily(hotel, date, closed_by):
    closing, _ = DailyClosing.objects.select_for_update().get_or_create(
        hotel=hotel, date=date
    )
    if closing.status == DailyClosingStatus.CLOSED:
        raise AlreadyClosedError(f"Date {date} is already closed.")

    totals = FinancialTransaction.objects.filter(
        hotel=hotel,
        transaction_date=date,
        is_deleted=False,
    ).values('currency', 'transaction_type').annotate(total=Sum('amount'))

    # Build income/expense dicts by currency
    income_by_currency = {}
    expense_by_currency = {}
    for row in totals:
        currency = row['currency']
        total = str(row['total'])  # Store as string in JSONField for precision
        if row['transaction_type'] == TransactionType.INCOME:
            income_by_currency[currency] = total
        else:
            expense_by_currency[currency] = total

    closing.status = DailyClosingStatus.CLOSED
    closing.total_income_by_currency = income_by_currency
    closing.total_expense_by_currency = expense_by_currency
    closing.closed_by = closed_by
    closing.closed_at = timezone.now()
    closing.save()
    return closing
```

> [!NOTE]
> Storing Decimal values as strings inside `JSONField` preserves full precision. When reading them back, they should be converted to `Decimal` via `Decimal(value)` before any arithmetic.

---

### 5.4 `ClosingService.close_monthly(hotel, year, month, closed_by)`

**Purpose:** Performs the monthly financial close by aggregating all daily closings for the month.

**Prerequisite Validation:**

- Determines the set of all calendar dates in `(year, month)` for the hotel's operational period.
- Queries all `DailyClosing` records for `(hotel, year, month)`.
- If any calendar date in the month does not have a `DailyClosing` with `status=CLOSED`, raises `UnclosedDailyClosingsError` listing the open dates.

**Aggregation:**

- Iterates over all `DailyClosing` records for the month.
- Merges `total_income_by_currency` and `total_expense_by_currency` JSON dicts, summing values by currency key using `Decimal` arithmetic.
- Creates a `MonthlyClosing` record with the aggregated totals.

**Error Cases:**

| Exception | Condition |
|---|---|
| `UnclosedDailyClosingsError` | One or more daily closings for the month are not `CLOSED` |
| `AlreadyClosedError` | Monthly closing already exists with `status=CLOSED` |

---

## 6. Celery Tasks | ٦. المهام الخلفية غير المتزامنة (Celery Tasks)

> 💡 **شرح المهام الخلفية:**
> - `auto_close_previous_day`: تعمل تلقائياً عبر Celery Beat في الساعة 01:00 فجراً لإغلاق اليوم السابق.
> - `export_financial_report`: مهمة غير متزامنة لتوليد التقارير المالية الكبيرة (PDF/Excel) في الخلفية دون تجميد استجابة المستخدم.

Celery is used to offload two categories of work from the synchronous request/response cycle:

1. **Scheduled automatic daily closing** — runs at a fixed time each night.
2. **Async report export** — triggered by API request, result polled by client.

### 6.1 `auto_close_previous_day`

| Property | Value |
|---|---|
| **Schedule** | Celery Beat, `01:00` daily (server timezone) |
| **Queue** | `finance` |
| **Max Retries** | 3 |
| **Retry Delay** | 300 seconds (5 minutes) |
| **Trigger Condition** | `HotelSettings.auto_close_daily == True` |

**Behavior:**

1. Computes `yesterday = date.today() - timedelta(days=1)`.
2. Queries all hotels where `settings__auto_close_daily=True`.
3. For each hotel, calls `ClosingService.close_daily(hotel, yesterday, closed_by=None)`.
4. If `AlreadyClosedError` is raised (e.g., was already manually closed), silently skips.
5. If any other exception occurs, retries up to 3 times with a 300-second countdown.
6. Failed retries after max attempts are logged to Celery error log and monitored via Sentry.

**Task Definition Skeleton:**

```python
@shared_task(bind=True, max_retries=3)
def auto_close_previous_day(self):
    yesterday = date.today() - timedelta(days=1)
    hotels = Hotel.objects.filter(
        settings__auto_close_daily=True
    ).select_related('settings')
    for hotel in hotels:
        try:
            ClosingService.close_daily(hotel, yesterday, closed_by=None)
        except AlreadyClosedError:
            pass  # Already closed, skip
        except Exception as exc:
            self.retry(exc=exc, countdown=300)
```

**Celery Beat Configuration (`config/celery_beat.py`):**

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'auto-close-previous-day': {
        'task': 'finance.tasks.auto_close_previous_day',
        'schedule': crontab(hour=1, minute=0),
    },
    # ... other beat tasks
}
```

---

### 6.2 `export_financial_report`

| Property | Value |
|---|---|
| **Trigger** | `POST /api/v1/finance/export/` |
| **Return** | Immediate response with `task_id` |
| **Output Formats** | CSV, PDF (specified by `format` request parameter) |
| **Status Poll** | `GET /api/v1/finance/export/{task_id}/status/` |
| **Completion** | Response includes `download_url` for the generated file |

**Request / Response Flow:**

```
Client                          API Server                      Celery Worker
  │                                  │                                │
  │  POST /api/v1/finance/export/    │                                │
  │  {hotel, date_from, date_to,     │                                │
  │   format: "csv"}                 │                                │
  │─────────────────────────────────>│                                │
  │                                  │── export_financial_report.     │
  │                                  │   delay(hotel_id, ...)  ──────>│
  │  HTTP 202 Accepted               │                                │
  │  {task_id: "abc-123"}            │                                │
  │<─────────────────────────────────│                                │
  │                                  │                                │
  │  GET /api/v1/finance/export/     │                                │
  │      abc-123/status/             │                                │
  │─────────────────────────────────>│                                │
  │  {status: "PENDING"}             │                                │
  │<─────────────────────────────────│                                │
  │                                  │         (task completes)       │
  │  GET /api/v1/finance/export/     │                                │
  │      abc-123/status/             │                                │
  │─────────────────────────────────>│                                │
  │  {status: "SUCCESS",             │                                │
  │   download_url: "..."}           │                                │
  │<─────────────────────────────────│                                │
```

**Task Definition Skeleton:**

```python
@shared_task(bind=True, max_retries=3)
def export_financial_report(self, hotel_id, date_from, date_to, format='csv'):
    try:
        hotel = Hotel.objects.get(id=hotel_id)
        report_data = FinanceService.get_period_summary(hotel, date_from, date_to)
        file_path = ReportExporter.export(report_data, format=format)
        return {'status': 'SUCCESS', 'file_path': str(file_path)}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

---

## 7. API Endpoints | ٧. نقاط النهاية للواجهات المالية (REST Endpoints)

> 💡 **شرح نقاط النهاية:** جدول يوضح جميع نقاط النهاية المتاحة لوسائل الدفع، تسجيل المدفوعات، استعراض المعاملات، أسعار الصرف، والإغلاقات الدورية.

All endpoints require a valid JWT access token in the `Authorization: Bearer <token>` header. Permissions are enforced via the custom RBAC permission system introduced in Phase 3.

| Method | Endpoint | Description | Required Auth |
|---|---|---|---|
| `GET` | `/api/v1/payments/methods/` | List all active payment methods for the hotel | JWT + `payments.view` |
| `POST` | `/api/v1/payments/methods/` | Create a new payment method | JWT + `payments.manage` |
| `GET` | `/api/v1/payments/` | List payments with filters (date range, currency, method, reservation) | JWT + `payments.view` |
| `POST` | `/api/v1/payments/` | Record a new payment (auto-creates FinancialTransaction) | JWT + `payments.manage` |
| `DELETE` | `/api/v1/payments/{id}/` | Soft-delete a payment (sets `is_deleted=True`) | JWT + `payments.manage` |
| `GET` | `/api/v1/finance/categories/` | List finance categories | JWT + `finance.view` |
| `POST` | `/api/v1/finance/categories/` | Create a new finance category | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/transactions/` | List financial transactions with filters | JWT + `finance.view` |
| `POST` | `/api/v1/finance/transactions/` | Create a manual financial transaction | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/summary/daily/` | Get daily income/expense summary grouped by currency | JWT + `finance.view` |
| `POST` | `/api/v1/finance/closings/daily/` | Close a specific date for the hotel | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/closings/daily/` | List daily closings with status and totals | JWT + `finance.view` |
| `POST` | `/api/v1/finance/closings/monthly/` | Close a specific month (requires all daily closings closed) | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/exchange-rates/` | List stored exchange rates | JWT + `finance.view` |
| `POST` | `/api/v1/finance/export/` | Trigger async report export; returns `task_id` immediately | JWT + `finance.manage` |
| `GET` | `/api/v1/finance/export/{task_id}/status/` | Poll export task status; returns `download_url` on completion | JWT + `finance.view` |

### Notable Endpoint Behaviors

- **`DELETE /api/v1/payments/{id}/`** — Returns `HTTP 204 No Content`. The record is soft-deleted. Re-deleting an already soft-deleted record returns `HTTP 404`.
- **`POST /api/v1/finance/closings/daily/`** — Returns `HTTP 409 Conflict` with `AlreadyClosedError` if the date is already closed.
- **`POST /api/v1/finance/closings/monthly/`** — Returns `HTTP 422 Unprocessable Entity` with a list of unclosed dates if any daily closing is not `CLOSED`.
- **`POST /api/v1/finance/export/`** — Returns `HTTP 202 Accepted` immediately with `{"task_id": "<uuid>"}`.
- **`GET /api/v1/finance/export/{task_id}/status/`** — Returns `{"status": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE", "download_url": null | "<url>"}`.

---

## 8. Permissions | ٨. مصفوفة الصلاحيات المالية والأمان المحاسبي

> 💡 **شرح الصلاحيات:** فصل صلاحيات العرض (`payments.view`, `finance.view`) عن صلاحيات الإدارة والتحصيل والإغلاق (`payments.manage`, `finance.manage`) لحماية أمان الصندوق.

Phase 6 introduces two permission namespaces: `payments` and `finance`. These integrate with the existing RBAC system.

### `payments` Namespace

| Permission | Description | Typical Roles |
|---|---|---|
| `payments.view` | Read-only access to payments and payment methods | Receptionist, Manager, Admin |
| `payments.manage` | Create payments, soft-delete payments, create/update payment methods | Receptionist, Manager, Admin |

### `finance` Namespace

| Permission | Description | Typical Roles |
|---|---|---|
| `finance.view` | Read-only access to transactions, categories, summaries, exchange rates, closings | Manager, Admin, Accountant |
| `finance.manage` | Create/soft-delete transactions, create/update categories, perform daily/monthly closings, trigger exports | Manager, Admin, Accountant |

### Permission Enforcement

Permissions are checked in DRF views using the custom `HasHotelPermission` permission class:

```python
class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasHotelPermission]

    def get_required_permission(self):
        if self.action in ['list', 'retrieve']:
            return 'payments.view'
        return 'payments.manage'
```

Hotel staff can only access data belonging to their assigned hotel. Cross-hotel data access is rejected at the queryset level via `get_queryset()` scoping.

---

## 9. Tests Summary | ٩. ملخص نتائج الاختبارات الآلية (14 اختباراً ناجحاً)

> 💡 **ملخص الاختبارات:** 14 اختباراً دقيقاً يشمل حظر التعديل على التواريخ المغلقة، منع الإغلاق المزدوج، التحقق من دقة التجميع بحسب العملة، والحذف المرن.

Phase 6 includes **14 automated tests** covering all critical financial paths.

### Test Matrix

| # | Test Name | Category | What It Verifies |
|---|---|---|---|
| 1 | `test_payment_creates_financial_transaction` | Payment | Creating a `Payment` automatically creates a linked `FinancialTransaction` with `transaction_type=INCOME` |
| 2 | `test_payment_transaction_amounts_match` | Payment | The auto-created `FinancialTransaction` has the same `amount` and `currency` as the `Payment` |
| 3 | `test_payment_rejected_on_closed_date` | Payment | `PaymentService.create()` raises `DateClosedError` when `payment_date` is a `CLOSED` daily closing |
| 4 | `test_close_daily_idempotent_raises_error` | DailyClosing | Calling `ClosingService.close_daily()` twice on the same date raises `AlreadyClosedError` |
| 5 | `test_close_daily_idempotent_no_duplicate_record` | DailyClosing | Double-close does not create a duplicate `DailyClosing` row |
| 6 | `test_daily_closing_totals_by_currency_usd` | DailyClosing | Totals for USD transactions are correctly aggregated in `total_income_by_currency` |
| 7 | `test_daily_closing_totals_by_currency_mixed` | DailyClosing | Totals for mixed-currency transactions are grouped correctly without cross-currency sums |
| 8 | `test_monthly_closing_fails_with_open_daily` | MonthlyClosing | `ClosingService.close_monthly()` raises `UnclosedDailyClosingsError` if any daily closing is `OPEN` |
| 9 | `test_financial_transaction_soft_delete` | FinancialTransaction | Soft-deleting a transaction sets `is_deleted=True` and `deleted_at`, but does not remove the row |
| 10 | `test_financial_transaction_audit_trail_preserved` | FinancialTransaction | Soft-deleted transactions are visible when querying `FinancialTransaction.all_objects.all()` |
| 11 | `test_exchange_rate_not_used_in_closing` | ExchangeRate | `DailyClosing` totals are not affected by the presence or absence of `ExchangeRate` records |
| 12 | `test_auto_close_task_closes_previous_day` | Celery | `auto_close_previous_day` task closes yesterday's date for hotels with `auto_close_daily=True` |
| 13 | `test_auto_close_task_skips_already_closed` | Celery | Task does not raise when a daily closing is already `CLOSED`; silently skips |
| 14 | `test_auto_close_task_retries_on_error` | Celery | Task retries up to 3 times when an unexpected exception occurs |

### Running the Tests

```bash
# Run all Phase 6 tests
python manage.py test tests.test_finance

# Run with coverage report
coverage run manage.py test tests.test_finance
coverage report -m --include="payments/*,finance/*"
```

---

## 10. Files Changed | ١٠. جدول الملفات المنشأة والمعدلة

> 💡 **دليل الملفات:** قائمة بالملفات المضافة في تطبيقي `payments` و `finance` مع ملفات الاختبارات والمهام المجدولة.

### New Files

| File | Action | What Changed |
|---|---|---|
| [`payments/models.py`](../payments/models.py) | **CREATED** | `PaymentMethod` and `Payment` (soft-delete) models; `ActivePaymentManager` |
| [`payments/services.py`](../payments/services.py) | **CREATED** | `PaymentService` with date-closed validation and auto-transaction creation |
| [`payments/serializers.py`](../payments/serializers.py) | **CREATED** | `PaymentMethodSerializer`, `PaymentSerializer`, `PaymentCreateSerializer` |
| [`payments/views.py`](../payments/views.py) | **CREATED** | `PaymentMethodViewSet`, `PaymentViewSet` with soft-delete action |
| [`payments/urls.py`](../payments/urls.py) | **CREATED** | URL routing for `/api/v1/payments/` |
| [`finance/models.py`](../finance/models.py) | **CREATED** | `FinanceCategory`, `FinancialTransaction`, `ExchangeRate`, `DailyClosing`, `MonthlyClosing` |
| [`finance/services.py`](../finance/services.py) | **CREATED** | `FinanceService.get_daily_summary()`, `ClosingService.close_daily()`, `ClosingService.close_monthly()` |
| [`finance/selectors.py`](../finance/selectors.py) | **CREATED** | Financial summary queries, transaction list selectors with currency grouping |
| [`finance/tasks.py`](../finance/tasks.py) | **CREATED** | `auto_close_previous_day` (scheduled), `export_financial_report` (async) Celery tasks |
| [`finance/serializers.py`](../finance/serializers.py) | **CREATED** | Finance serializers; `DailyClosingSerializer` with per-currency breakdown output |
| [`finance/views.py`](../finance/views.py) | **CREATED** | Finance ViewSets: categories, transactions, closings, exchange rates, export |
| [`finance/urls.py`](../finance/urls.py) | **CREATED** | URL routing for `/api/v1/finance/` |
| [`tests/test_finance.py`](../tests/test_finance.py) | **CREATED** | 14 finance and payments tests covering all critical paths |

### Modified Files

| File | Action | What Changed |
|---|---|---|
| [`config/celery_beat.py`](../config/celery_beat.py) | **MODIFIED** | Added `auto_close_previous_day` to `CELERY_BEAT_SCHEDULE` at `01:00` daily |

---

## 11. Migrations | ١١. ترحيلات قاعدة البيانات للمرحلة السادسة

> 💡 **شرح المايجريشن:** يوثق إنشاء جداول المدفوعات، المعاملات، أسعار الصرف، وسجلات الإغلاقات اليومية والشهرية مع الفهارس المركبة.

### `payments/migrations/0001_initial.py`

Creates the following tables:

| Table | Description |
|---|---|
| `payments_paymentmethod` | PaymentMethod records scoped to hotel |
| `payments_payment` | Payment ledger with soft-delete columns (`is_deleted`, `deleted_at`) |

Key migration operations:
- Creates `payments_paymentmethod` with unique constraint `(hotel_id, name)`.
- Creates `payments_payment` with `DecimalField(max_digits=10, decimal_places=2)` for `amount`.
- Adds index on `payments_payment(hotel_id, payment_date)` for date-range queries.
- Adds index on `payments_payment(is_deleted)` for soft-delete filtering performance.

```bash
python manage.py makemigrations payments
python manage.py migrate payments
```

---

### `finance/migrations/0001_initial.py`

Creates the following tables:

| Table | Description |
|---|---|
| `finance_financecategory` | Income/expense category catalogue |
| `finance_financialtransaction` | Immutable financial transaction ledger |
| `finance_exchangerate` | Exchange rate reference (display only) |
| `finance_dailyclosing` | Daily closing records with JSON currency totals |
| `finance_monthlyclosing` | Monthly closing records aggregated from daily closings |

Key migration operations:
- Creates `finance_financialtransaction` with `DecimalField(max_digits=10, decimal_places=2)` for `amount`.
- Creates `finance_dailyclosing` with `UniqueConstraint(fields=['hotel_id', 'date'])`.
- Creates `finance_monthlyclosing` with `UniqueConstraint(fields=['hotel_id', 'year', 'month'])`.
- Creates `finance_exchangerate` with `UniqueConstraint(fields=['from_currency', 'to_currency', 'date'])`.
- Adds index on `finance_financialtransaction(hotel_id, transaction_date, is_deleted)` for daily summary queries.

```bash
python manage.py makemigrations finance
python manage.py migrate finance
```

---

### Full Migration Sequence for Phase 6

```bash
# Generate migration files
python manage.py makemigrations payments finance

# Review generated migrations before applying
python manage.py sqlmigrate payments 0001_initial
python manage.py sqlmigrate finance 0001_initial

# Apply to database
python manage.py migrate

# Verify
python manage.py showmigrations payments finance
```

---

*End of Phase 6 Documentation*
